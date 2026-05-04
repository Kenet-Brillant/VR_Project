// MQTTController.cs — Controller générique pur C#
// ─────────────────────────────────────────────────────────────────────────────
// ✅ Plug and play — copier avec MQTTClient.cs
// ✅ Compatible Unity et hors Unity
//
// UTILISATION
// ───────────
//   var controller = new MQTTController();
//   controller.TopicCommandes = "unity/boules/commands";
//   controller.TopicEcoute    = "jeu/boules/#";
//   controller.OnMessageRecu += (topic, data) => Console.WriteLine(data["evenement"]);
//   controller.Start();
//
//   controller.EnvoyerCommande(new Dictionary<string, object>
//   {
//       { "taille", 1.5 },
//       { "nombre", 10  }
//   });
//
//   controller.Stop();
// ─────────────────────────────────────────────────────────────────────────────

using System;
using System.Collections.Generic;

public class MQTTController
{
    // ── Configuration ───────────────────────────────────────────────────
    public string TopicCommandes { get; set; } = "unity/generic/commands";
    public string TopicEcoute    { get; set; } = "jeu/generic/#";
    public Action<string> Logger { get; set; } = msg => Console.WriteLine(msg);

    // ── Événements ──────────────────────────────────────────────────────
    public event Action<string, Dictionary<string, string>> OnMessageRecu;
    public event Action OnConnecte;
    public event Action<string> OnDeconnecte;

    // ── Interne ─────────────────────────────────────────────────────────
    private readonly MQTTClient _client = new MQTTClient();

    // ── Démarrage / Arrêt ───────────────────────────────────────────────

    public void Start()
    {
        _client.Logger           = Logger;
        _client.OnConnected     += () =>
        {
            _client.Subscribe(TopicEcoute);
            OnConnecte?.Invoke();
            Logger?.Invoke($"🎮 Controller prêt — écoute sur : {TopicEcoute}");
            Logger?.Invoke($"📤 Commandes vers : {TopicCommandes}");
        };
        _client.OnDisconnected  += reason => OnDeconnecte?.Invoke(reason);
        _client.OnMessageReceived += HandleMessage;
        _client.Connect();
    }

    public void Stop()
    {
        _client.OnMessageReceived -= HandleMessage;
        _client.Disconnect();
        Logger?.Invoke("🛑 Controller arrêté.");
    }

    // ── Envoi de commandes ───────────────────────────────────────────────

    /// <summary>
    /// Envoie une commande vers Unity.
    /// Le dictionnaire peut contenir n'importe quelles clés selon le jeu.
    /// </summary>
    public bool EnvoyerCommande(Dictionary<string, object> parametres)
    {
        if (!parametres.ContainsKey("timestamp"))
            parametres["timestamp"] = GetTimestamp();

        bool ok = _client.Publish(TopicCommandes, parametres);
        Logger?.Invoke(ok ? $"✅ Commande envoyée sur [{TopicCommandes}]"
                          : "❌ Échec envoi commande");
        return ok;
    }

    /// <summary>
    /// Envoie une commande simple avec un seul paramètre "action".
    /// </summary>
    public bool EnvoyerAction(string action)
    {
        return EnvoyerCommande(new Dictionary<string, object> { { "action", action } });
    }

    // ── Réception des messages ───────────────────────────────────────────

    private void HandleMessage(string topic, string json)
    {
        try
        {
            Logger?.Invoke($"📨 Message reçu de Unity sur [{topic}]");
            Dictionary<string, string> data = MQTTClient.JsonToDict(json);
            OnMessageRecu?.Invoke(topic, data);
        }
        catch (Exception ex)
        {
            Logger?.Invoke($"❌ Erreur traitement message : {ex.Message}");
        }
    }

    // ── Utilitaire ───────────────────────────────────────────────────────

    private static double GetTimestamp()
    {
        return (DateTime.UtcNow - new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc)).TotalSeconds;
    }
}
