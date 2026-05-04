// MQTTPublisher.cs — Publisher générique
// ─────────────────────────────────────────────────────────────────────────────
// ✅ Plug and play — copier dans Assets/ avec MQTTClient.cs
// ✅ Compatible toutes versions Unity et hors Unity
// ✅ Accessible via MQTTPublisher.Instance OU MQTTPublisher.instance
// ─────────────────────────────────────────────────────────────────────────────

using System;
using System.Collections.Generic;

public class MQTTPublisher
{
    // ── Singleton ── accessible en majuscule ET minuscule ───────────────────
    private static MQTTPublisher _instance;

    public static MQTTPublisher Instance
    {
        get
        {
            if (_instance == null) _instance = new MQTTPublisher();
            return _instance;
        }
    }

    // Alias minuscule — pour compatibilité avec tous les scripts
    public static MQTTPublisher instance => Instance;

    // ── Configuration ───────────────────────────────────────────────────────
    public string UserId { get; set; } = "joueur_1";
    public string Topic  { get; set; } = "jeu/generic/evenement";

    public Action<string> Logger
    {
        get => _client.Logger;
        set => _client.Logger = value;
    }

    public bool IsConnected => _client.IsConnected;

    // ── Interne ─────────────────────────────────────────────────────────────
    private readonly MQTTClient _client = new MQTTClient();

    // ── Démarrage / Arrêt ───────────────────────────────────────────────────

    public void Start()
    {
        _client.Connect();
    }

    public void Stop()
    {
        _client.Disconnect();
    }

    // ── Publication ─────────────────────────────────────────────────────────

    /// <summary>
    /// Publie un événement avec des données optionnelles.
    /// Ajoute automatiquement : user, evenement, timestamp.
    /// </summary>
    public bool Publish(string eventName, Dictionary<string, object> extraData = null)
    {
        var payload = new Dictionary<string, object>
        {
            { "user",      UserId    },
            { "evenement", eventName },
            { "timestamp", GetTimestamp() }
        };

        if (extraData != null)
            foreach (var kv in extraData)
                payload[kv.Key] = kv.Value;

        return _client.Publish(Topic, payload);
    }

    /// <summary>
    /// Publie un JSON brut sur le topic par défaut.
    /// </summary>
    public bool PublishRaw(string json)
    {
        return _client.PublishRaw(Topic, json);
    }

    /// <summary>
    /// Publie un JSON brut sur un topic spécifique.
    /// </summary>
    public bool PublishRaw(string topic, string json)
    {
        return _client.PublishRaw(topic, json);
    }

    // ── Utilitaire ──────────────────────────────────────────────────────────

    private static double GetTimestamp()
    {
        return (DateTime.UtcNow - new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc)).TotalSeconds;
    }
}
