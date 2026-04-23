// UnityStressReporter.cs
// ─────────────────────────────────────────────────────────────────────────────
// Script Unity à ajouter dans la scène pendant le stress test.
// Il mesure les FPS et le nombre d'objets en scène, puis publie
// ces infos via MQTT pour que unity_stress_test.py puisse les lire.
//
// UTILISATION :
//   1. Copier ce fichier dans Assets/script/
//   2. Créer un GameObject vide dans la scène → nommer "StressReporter"
//   3. Attacher ce script au GameObject
//   4. Lancer le jeu ▶️ puis lancer unity_stress_test.py
//   5. Retirer le script après les tests (pas besoin en production)
// ─────────────────────────────────────────────────────────────────────────────

using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using MQTTGeneric;

public class UnityStressReporter : MonoBehaviour
{
    // ── Config ──────────────────────────────────────────────────────────────
    [Header("Fréquence de rapport (secondes)")]
    public float intervalle = 0.5f;   // publie les FPS toutes les 0.5s

    // ── Interne ─────────────────────────────────────────────────────────────
    private float   _timer      = 0f;
    private float   _fpsAccum   = 0f;
    private int     _fpsFrames  = 0;
    private float   _fpsMoyenne = 0f;

    void Start()
    {
        // MQTTPublisher est déjà démarré par CircleManager
        // Rien à faire ici
        Debug.Log("📊 StressReporter démarré — publication FPS toutes les " + intervalle + "s");
    }

    void Update()
    {
        // Accumule les FPS
        _fpsAccum  += Time.timeScale / Time.deltaTime;
        _fpsFrames++;
        _timer     += Time.deltaTime;

        if (_timer >= intervalle)
        {
            _fpsMoyenne = _fpsAccum / _fpsFrames;
            _fpsAccum   = 0f;
            _fpsFrames  = 0;
            _timer      = 0f;

            PublierMetriques();
        }
    }

    void PublierMetriques()
    {
        // Compte les objets actifs dans la scène
        int nbObjets = FindObjectsByType<GameObject>(FindObjectsSortMode.None).Length;

        // Publie les FPS sur un topic dédié
        MQTTPublisher.Instance.PublishRaw(
            "jeu/stress/fps",
            MQTTGeneric.MQTTClient.DictToJson(new Dictionary<string, object>
            {
                { "fps",       Mathf.Round(_fpsMoyenne * 10f) / 10f },
                { "nb_objets", nbObjets },
                { "timestamp", GetTimestamp() }
            })
        );

        // Affiche aussi dans la Console Unity
        string alerte = _fpsMoyenne < 30 ? " ⚠️ FPS BAS !" : "";
        Debug.Log($"📊 FPS : {_fpsMoyenne:F1} | Objets : {nbObjets}{alerte}");
    }

    private static double GetTimestamp()
    {
        return (System.DateTime.UtcNow - new System.DateTime(1970, 1, 1)).TotalSeconds;
    }

    // Propriété pour vérifier si MQTTPublisher est connecté
    // (nécessite d'exposer IsConnected dans MQTTPublisher.cs)
}
