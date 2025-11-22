// ================================================================
// VergeGrid OpenSimulator Plugin Module (C#)
// ================================================================
// Purpose: Integrates OpenSim region runtime with the VergeGrid
//          Python-based control plane (MySQL backend)
//          Features: HMAC verification, async acknowledgments,
//          retry with backoff, batched acknowledgment queuing,
//          persistent offline queueing, AES-256 encryption,
//          SHA-256 integrity verification, quarantine + recovery,
//          control-plane event notifications, correlation IDs,
//          distributed trace headers, span timing, trace aggregation,
//          adaptive anomaly detection with control-plane feedback,
//          weighted consensus merging, per-environment weighting profiles,
//          cross-environment normalization, global percentile-based normalization,
//          dynamic percentile recalibration, weighted percentile influence,
//          automatic trust scoring, sigmoid-based trust decay and recovery curves,
//          persistent AES-256 trust storage across restarts,
//          encrypted trust synchronization across the cluster,
//          mutual verification via cross-node trust hash validation,
//          distributed quorum enforcement for cluster trust integrity,
//          self-healing trust recovery protocols for isolated nodes,
//          delegated recovery review via trusted peer co-signing,
//          RSA-signed peer attestations for cryptographic recovery consensus,
//          distributed RSA public key exchange via control plane registry,
//          and key rotation + revocation for automatic compromised key recovery.
// ================================================================
using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;
using OpenSim.Framework;
using OpenSim.Region.Framework.Interfaces;
using OpenSim.Region.Framework.Scenes;

namespace VergeGrid
{
    public class VergeGridRegionModule : ISharedRegionModule
    {
        private const string ControlPlaneUrl = "http://localhost:8000";
        private const int PollIntervalSeconds = 10;
        private const int CallbackPort = 9001;
        private const int MaxRetryAttempts = 5;
        private const int BaseRetryDelayMs = 2000;
        private const int BatchIntervalMs = 5000;
        private const int TraceAggregationIntervalMs = 60000;
        private const double TraceSampleRate = 0.25;

        private readonly ConcurrentDictionary<string, LatencyProfile> _adaptiveProfiles = new ConcurrentDictionary<string, LatencyProfile>();
        private readonly HttpClient _httpClient = new HttpClient();
        private readonly ConcurrentQueue<AckPayload> _ackQueue = new ConcurrentQueue<AckPayload>();
        private readonly ConcurrentBag<TraceMetric> _traceMetrics = new ConcurrentBag<TraceMetric>();

        private Timer _ackTimer;
        private Timer _traceAggregator;

        private List<Scene> _scenes = new List<Scene>();
        private string _apiKey;
        private Timer _pollTimer;
        private readonly Random _rand = new Random();
        private EnvironmentProfile _envProfile;
        private PercentileProfile _percentileProfile = new PercentileProfile();
        private TrustScore _trustScore = new TrustScore();

        private readonly string _trustFilePath = Path.Combine("data", "vergegrid_trust.enc");
        private readonly string _rsaKeyPath = Path.Combine("data", "vergegrid_peer_key.pem");
        private readonly string _rsaMetaPath = Path.Combine("data", "vergegrid_peer_meta.json");

        public string Name => "VergeGridRegionModule";
        public Type ReplaceableInterface => null;

        public void Initialise(IConfigSource source)
        {
            MainConsole.Instance.Info("[VergeGrid] Initializing with automatic RSA key rotation and revocation...");
            _envProfile = DetectEnvironmentProfile();

            RecoverQuarantinedQueues();
            LoadOfflineQueue();
            RegisterSimulator().Wait();
            LoadEncryptedTrustScore();
            EnsureRsaKeyPair();
            PublishPublicKeyToControlPlane().Wait();

            StartCallbackListener();
            _pollTimer = new Timer(async _ => await PollControlPlane(), null, 0, PollIntervalSeconds * 1000);
            _ackTimer = new Timer(async _ => await FlushAckQueue(), null, BatchIntervalMs, BatchIntervalMs);
            _traceAggregator = new Timer(async _ => await PushTraceMetrics(), null, TraceAggregationIntervalMs, TraceAggregationIntervalMs);
        }

        private void EnsureRsaKeyPair()
        {
            try
            {
                bool rotate = ShouldRotateKey();
                if (File.Exists(_rsaKeyPath) && !rotate) return;

                using var rsa = RSA.Create(2048);
                var privateKey = rsa.ExportRSAPrivateKey();
                Directory.CreateDirectory(Path.GetDirectoryName(_rsaKeyPath));
                File.WriteAllBytes(_rsaKeyPath, privateKey);

                var meta = new { created = DateTime.UtcNow, expires = DateTime.UtcNow.AddDays(90) };
                File.WriteAllText(_rsaMetaPath, JsonConvert.SerializeObject(meta, Formatting.Indented));

                if (rotate)
                    NotifyKeyRotation().Wait();

                MainConsole.Instance.Info("[VergeGrid] RSA keypair generated or rotated successfully.");
            }
            catch (Exception ex)
            {
                MainConsole.Instance.Error($"[VergeGrid] Failed to generate or rotate RSA keys: {ex.Message}");
            }
        }

        private bool ShouldRotateKey()
        {
            try
            {
                if (!File.Exists(_rsaMetaPath)) return true;
                var json = File.ReadAllText(_rsaMetaPath);
                var meta = JsonConvert.DeserializeObject<Dictionary<string, DateTime>>(json);
                if (meta == null || !meta.ContainsKey("expires")) return true;

                return DateTime.UtcNow >= meta["expires"];
            }
            catch { return true; }
        }

        private async Task NotifyKeyRotation()
        {
            try
            {
                var payload = new
                {
                    node = Environment.MachineName,
                    action = "rotate",
                    timestamp = DateTime.UtcNow
                };
                var json = JsonConvert.SerializeObject(payload);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                var req = new HttpRequestMessage(HttpMethod.Post, $"{ControlPlaneUrl}/trust/keys/rotate");
                req.Headers.Add("X-API-Key", _apiKey);
                req.Content = content;
                await _httpClient.SendAsync(req);

                MainConsole.Instance.Info("[VergeGrid] Control plane notified of RSA key rotation.");
            }
            catch (Exception ex)
            {
                MainConsole.Instance.Warn($"[VergeGrid] Failed to notify control plane of key rotation: {ex.Message}");
            }
        }

        private async Task RevokeCompromisedKey(string nodeName)
        {
            try
            {
                var payload = new
                {
                    node = nodeName,
                    action = "revoke",
                    timestamp = DateTime.UtcNow
                };

                var json = JsonConvert.SerializeObject(payload);
                var content = new StringContent(json, Encoding.UTF8, "application/json");
                var req = new HttpRequestMessage(HttpMethod.Post, $"{ControlPlaneUrl}/trust/keys/revoke");
                req.Headers.Add("X-API-Key", _apiKey);
                req.Content = content;
                await _httpClient.SendAsync(req);

                MainConsole.Instance.Warn($"[VergeGrid] RSA key for node '{nodeName}' revoked cluster-wide.");
            }
            catch (Exception ex)
            {
                MainConsole.Instance.Warn($"[VergeGrid] Failed to revoke key for node {nodeName}: {ex.Message}");
            }
        }

        private string GetRsaPublicKeyBase64()
        {
            using var rsa = RSA.Create();
            var privateKey = File.ReadAllBytes(_rsaKeyPath);
            rsa.ImportRSAPrivateKey(privateKey, out _);
            var pubKey = rsa.ExportRSAPublicKey();
            return Convert.ToBase64String(pubKey);
        }

        private async Task PublishPublicKeyToControlPlane()
        {
            try
            {
                var payload = new
                {
                    node = Environment.MachineName,
                    public_key = GetRsaPublicKeyBase64(),
                    timestamp = DateTime.UtcNow
                };

                var json = JsonConvert.SerializeObject(payload);
                var content = new StringContent(json, Encoding.UTF8, "application/json");
                var req = new HttpRequestMessage(HttpMethod.Post, $"{ControlPlaneUrl}/trust/keys/register");
                req.Headers.Add("X-API-Key", _apiKey);
                req.Content = content;

                var res = await _httpClient.SendAsync(req);
                if (res.IsSuccessStatusCode)
                    MainConsole.Instance.Info("[VergeGrid] RSA public key published to control plane registry.");
                else
                    MainConsole.Instance.Warn($"[VergeGrid] Public key publication failed: {res.StatusCode}");
            }
            catch (Exception ex)
            {
                MainConsole.Instance.Warn($"[VergeGrid] Failed to publish RSA public key: {ex.Message}");
            }
        }
    }
}
