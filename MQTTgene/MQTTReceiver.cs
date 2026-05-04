// MQTTReceiver.cs — Receiver générique
// ─────────────────────────────────────────────────────────────────────────────
// ✅ Plug and play — copier dans Assets/ avec MQTTClient.cs
// ✅ Compatible toutes versions Unity et hors Unity
//
// UTILISATION DANS UNITY
// ──────────────────────
//   void Start()
//   {
//       MQTTReceiver.Instance.Topic = "unity/monprojet/commands";
//       MQTTReceiver.Instance.Start();
//       MQTTReceiver.OnCommandReceived += HandleCommand;
//   }
//
//   void OnDestroy()
//   {
//       MQTTReceiver.OnCommandReceived -= HandleCommand;
//       MQTTReceiver.Instance.Stop();
//   }
//
//   void HandleCommand(Dictionary<string, string> data)
//   {
//       // Dispatch vers le thread principal Unity (voir exemple en bas)
//       _mainThreadQueue.Enqueue(() =>
//       {
//           if (data.ContainsKey("vitesse"))
//               speed = float.Parse(data["vitesse"],
//                   System.Globalization.CultureInfo.InvariantCulture);
//       });
//   }
//
// ⚠️ Les callbacks arrivent sur un thread secondaire.
//    Utilisez une Queue pour modifier des GameObjects (voir exemple en bas).
// ─────────────────────────────────────────────────────────────────────────────

using System;
using System.Collections.Generic;

public class MQTTReceiver
{
    // ── Singleton ───────────────────────────────────────────────────────
    private static MQTTReceiver _instance;
    public static MQTTReceiver Instance
    {
        get
        {
            if (_instance == null) _instance = new MQTTReceiver();
            return _instance;
        }
    }

    // ── Événement principal ─────────────────────────────────────────────
    /// <summary>
    /// Déclenché quand une commande est reçue.
    /// ⚠️ Arrive sur un thread secondaire — utiliser une Queue dans Unity.
    /// </summary>
    public static event Action<Dictionary<string, string>> OnCommandReceived;

    // ── Configuration ───────────────────────────────────────────────────
    public string Topic { get; set; } = "unity/generic/commands";

    public Action<string> Logger
    {
        get => _client.Logger;
        set => _client.Logger = value;
    }

    // ── Interne ─────────────────────────────────────────────────────────
    private readonly MQTTClient _client = new MQTTClient();

    // ── Démarrage / Arrêt ───────────────────────────────────────────────

    public void Start()
    {
        _client.OnMessageReceived += HandleRawMessage;
        _client.OnConnected       += () => _client.Subscribe(Topic);
        _client.Connect();
    }

    public void Stop()
    {
        _client.OnMessageReceived -= HandleRawMessage;
        _client.Disconnect();
    }

    // ── Réception ───────────────────────────────────────────────────────

    private void HandleRawMessage(string topic, string json)
    {
        try
        {
            Logger?.Invoke($"📩 Commande reçue sur [{topic}] : {json}");
            Dictionary<string, string> data = MQTTClient.JsonToDict(json);
            OnCommandReceived?.Invoke(data);
        }
        catch (Exception ex)
        {
            Logger?.Invoke($"❌ Erreur traitement commande : {ex.Message}");
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// EXEMPLE : MainThreadDispatcher pour Unity
// ─────────────────────────────────────────────────────────────────────────────
//
//   private Queue<Action> _mainThreadQueue = new Queue<Action>();
//
//   void Update()
//   {
//       while (_mainThreadQueue.Count > 0)
//           _mainThreadQueue.Dequeue()?.Invoke();
//   }
//
//   void HandleCommand(Dictionary<string, string> data)
//   {
//       _mainThreadQueue.Enqueue(() =>
//       {
//           if (data.ContainsKey("vitesse"))
//               obstacleSpeed = float.Parse(data["vitesse"],
//                   System.Globalization.CultureInfo.InvariantCulture);
//       });
//   }
// ─────────────────────────────────────────────────────────────────────────────
