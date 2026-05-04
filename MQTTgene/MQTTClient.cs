// MQTTClient.cs — Implémentation MQTT 3.1.1 pure C#
// ─────────────────────────────────────────────────────────────────────────────
// ✅ ZÉRO dépendance externe — pas de M2Mqtt, pas de NuGet, pas de package
// ✅ Compatible Unity 2019, 2020, 2021, 2022, Unity 6 et toutes versions futures
// ✅ Compatible hors Unity (console, serveur...)
// ✅ Utilise uniquement System.Net.Sockets — inclus dans tout runtime .NET/Mono
// ✅ Plug and play — copier dans Assets/ et utiliser directement
// ─────────────────────────────────────────────────────────────────────────────

using System;
using System.Collections.Generic;
using System.Net.Sockets;
using System.Text;
using System.Threading;

public class MQTTClient
{
    // ── Configuration ───────────────────────────────────────────────────
    public string BrokerHost     { get; set; } = "devweb.estia.fr";
    public int    BrokerPort     { get; set; } = 1883;
    public string Username       { get; set; } = "estia";
    public string Password       { get; set; } = "*aZ9#r8X7";
    public string ClientId       { get; set; } = "unity_" + Guid.NewGuid().ToString("N").Substring(0, 8);
    public bool   AutoReconnect  { get; set; } = true;
    public int    ReconnectDelay { get; set; } = 3000;
    public int    KeepAlive      { get; set; } = 60;

    // ── Événements ──────────────────────────────────────────────────────
    public event Action                  OnConnected;
    public event Action<string>          OnDisconnected;
    public event Action<string, string>  OnMessageReceived;

    public Action<string> Logger { get; set; } = msg => Console.WriteLine(msg);

    // ── Interne ─────────────────────────────────────────────────────────
    private TcpClient       _tcp;
    private NetworkStream   _stream;
    private Thread          _readThread;
    private Thread          _pingThread;
    private bool            _running;
    private bool            _shouldReconnect = true;
    private ushort          _packetId = 1;
    private readonly List<string> _topics = new List<string>();
    private readonly object _writeLock = new object();

    // ── Connexion ────────────────────────────────────────────────────────

    public bool Connect()
    {
        try
        {
            _tcp    = new TcpClient();
            _tcp.Connect(BrokerHost, BrokerPort);
            _stream = _tcp.GetStream();

            SendConnect();

            byte[] connack = ReadPacket();
            if (connack == null || connack.Length < 4 || connack[0] != 0x20 || connack[3] != 0x00)
            {
                Logger?.Invoke("❌ CONNACK invalide — connexion refusée.");
                return false;
            }

            _running = true;

            _readThread = new Thread(ReadLoop) { IsBackground = true };
            _readThread.Start();

            _pingThread = new Thread(PingLoop) { IsBackground = true };
            _pingThread.Start();

            Logger?.Invoke($"✅ Connecté au broker MQTT : {BrokerHost}:{BrokerPort}");
            OnConnected?.Invoke();

            foreach (var t in _topics)
                SendSubscribe(t);

            return true;
        }
        catch (Exception ex)
        {
            Logger?.Invoke($"❌ Erreur connexion : {ex.Message}");
            return false;
        }
    }

    public void Disconnect()
    {
        _shouldReconnect = false;
        _running = false;
        try
        {
            lock (_writeLock)
                _stream?.Write(new byte[] { 0xE0, 0x00 }, 0, 2);
        }
        catch { }
        try { _tcp?.Close(); } catch { }
    }

    public bool IsConnected => _tcp != null && _tcp.Connected && _running;

    // ── Publication ──────────────────────────────────────────────────────

    public bool Publish(string topic, Dictionary<string, object> payload)
    {
        return PublishRaw(topic, DictToJson(payload));
    }

    public bool PublishRaw(string topic, string json)
    {
        if (!IsConnected)
        {
            Logger?.Invoke("⚠️ Publish ignoré — pas connecté.");
            return false;
        }
        try
        {
            byte[] topicBytes   = Encoding.UTF8.GetBytes(topic);
            byte[] payloadBytes = Encoding.UTF8.GetBytes(json);

            int remaining = 2 + topicBytes.Length + payloadBytes.Length;

            var packet = new List<byte>();
            packet.Add(0x30);
            EncodeLength(packet, remaining);
            packet.Add((byte)(topicBytes.Length >> 8));
            packet.Add((byte)(topicBytes.Length & 0xFF));
            packet.AddRange(topicBytes);
            packet.AddRange(payloadBytes);

            lock (_writeLock)
                _stream.Write(packet.ToArray(), 0, packet.Count);

            Logger?.Invoke($"➡️  Publié [{topic}] : {json}");
            return true;
        }
        catch (Exception ex)
        {
            Logger?.Invoke($"❌ Erreur publication : {ex.Message}");
            HandleDisconnect("Erreur publication");
            return false;
        }
    }

    // ── Abonnement ───────────────────────────────────────────────────────

    public void Subscribe(string topic)
    {
        if (!_topics.Contains(topic))
            _topics.Add(topic);

        if (IsConnected)
            SendSubscribe(topic);
    }

    // ── Paquets MQTT ─────────────────────────────────────────────────────

    private void SendConnect()
    {
        byte[] clientIdBytes = Encoding.UTF8.GetBytes(ClientId);
        byte[] userBytes     = Encoding.UTF8.GetBytes(Username);
        byte[] passBytes     = Encoding.UTF8.GetBytes(Password);

        var payload = new List<byte>();
        AppendString(payload, clientIdBytes);
        AppendString(payload, userBytes);
        AppendString(payload, passBytes);

        var varHeader = new List<byte>();
        AppendString(varHeader, Encoding.UTF8.GetBytes("MQTT"));
        varHeader.Add(0x04);
        varHeader.Add(0xC2);
        varHeader.Add((byte)(KeepAlive >> 8));
        varHeader.Add((byte)(KeepAlive & 0xFF));

        int remaining = varHeader.Count + payload.Count;

        var packet = new List<byte>();
        packet.Add(0x10);
        EncodeLength(packet, remaining);
        packet.AddRange(varHeader);
        packet.AddRange(payload);

        lock (_writeLock)
            _stream.Write(packet.ToArray(), 0, packet.Count);
    }

    internal void SendSubscribe(string topic)
    {
        byte[] topicBytes = Encoding.UTF8.GetBytes(topic);
        int remaining = 2 + 2 + topicBytes.Length + 1;

        var packet = new List<byte>();
        packet.Add(0x82);
        EncodeLength(packet, remaining);
        packet.Add((byte)(_packetId >> 8));
        packet.Add((byte)(_packetId & 0xFF));
        _packetId++;
        AppendString(packet, topicBytes);
        packet.Add(0x01);

        lock (_writeLock)
            _stream.Write(packet.ToArray(), 0, packet.Count);

        Logger?.Invoke($"📡 Abonné à : {topic}");
    }

    private void SendPing()
    {
        lock (_writeLock)
            _stream?.Write(new byte[] { 0xC0, 0x00 }, 0, 2);
    }

    // ── Boucle de lecture ────────────────────────────────────────────────

    private void ReadLoop()
    {
        while (_running)
        {
            try
            {
                byte[] packet = ReadPacket();
                if (packet == null) break;

                byte type = (byte)(packet[0] & 0xF0);

                if (type == 0x30)
                    HandlePublish(packet);
            }
            catch (Exception ex)
            {
                if (_running)
                {
                    Logger?.Invoke($"❌ Erreur lecture : {ex.Message}");
                    HandleDisconnect("Erreur lecture");
                }
                break;
            }
        }
    }

    private void HandlePublish(byte[] packet)
    {
        try
        {
            int idx = 1;
            int remaining = 0, mul = 1;
            byte b;
            do {
                b = packet[idx++];
                remaining += (b & 0x7F) * mul;
                mul *= 128;
            } while ((b & 0x80) != 0);

            int topicLen = (packet[idx] << 8) | packet[idx + 1];
            idx += 2;
            string topic = Encoding.UTF8.GetString(packet, idx, topicLen);
            idx += topicLen;

            int payloadLen = remaining - 2 - topicLen;
            string payload = Encoding.UTF8.GetString(packet, idx, payloadLen);

            OnMessageReceived?.Invoke(topic, payload);
        }
        catch (Exception ex)
        {
            Logger?.Invoke($"❌ Erreur traitement PUBLISH : {ex.Message}");
        }
    }

    private byte[] ReadPacket()
    {
        int first = _stream.ReadByte();
        if (first < 0) return null;

        int remaining = 0, mul = 1;
        byte b;
        do {
            int r = _stream.ReadByte();
            if (r < 0) return null;
            b = (byte)r;
            remaining += (b & 0x7F) * mul;
            mul *= 128;
        } while ((b & 0x80) != 0);

        byte[] data = new byte[remaining + 2];
        data[0] = (byte)first;
        data[1] = (byte)remaining;
        if (remaining > 0)
        {
            int read = 0;
            while (read < remaining)
            {
                int n = _stream.Read(data, 2 + read, remaining - read);
                if (n <= 0) return null;
                read += n;
            }
        }
        return data;
    }

    // ── Ping keepalive ───────────────────────────────────────────────────

    private void PingLoop()
    {
        while (_running)
        {
            Thread.Sleep(KeepAlive * 1000 / 2);
            if (_running && IsConnected)
            {
                try { SendPing(); }
                catch { }
            }
        }
    }

    // ── Reconnexion ──────────────────────────────────────────────────────

    private void HandleDisconnect(string reason)
    {
        if (!_running) return;
        _running = false;
        try { _tcp?.Close(); } catch { }
        OnDisconnected?.Invoke(reason);

        if (_shouldReconnect && AutoReconnect)
        {
            var t = new Thread(() => {
                Thread.Sleep(ReconnectDelay);
                Logger?.Invoke("🔄 Tentative de reconnexion...");
                Connect();
            }) { IsBackground = true };
            t.Start();
        }
    }

    // ── Utilitaires ──────────────────────────────────────────────────────

    private static void AppendString(List<byte> buf, byte[] str)
    {
        buf.Add((byte)(str.Length >> 8));
        buf.Add((byte)(str.Length & 0xFF));
        buf.AddRange(str);
    }

    private static void EncodeLength(List<byte> buf, int length)
    {
        do {
            byte enc = (byte)(length % 128);
            length /= 128;
            if (length > 0) enc |= 0x80;
            buf.Add(enc);
        } while (length > 0);
    }

    // ── JSON léger (sans dépendance) ─────────────────────────────────────

    public static string DictToJson(Dictionary<string, object> dict)
    {
        var sb = new StringBuilder("{");
        bool first = true;
        foreach (var kv in dict)
        {
            if (!first) sb.Append(",");
            first = false;
            sb.Append($"\"{kv.Key}\":{ValueToJson(kv.Value)}");
        }
        return sb.Append("}").ToString();
    }

    private static string ValueToJson(object v)
    {
        if (v == null)                              return "null";
        if (v is bool bv)                           return bv ? "true" : "false";
        if (v is string sv)                         return $"\"{sv.Replace("\"", "\\\"")}\"";
        if (v is float fv)                          return fv.ToString("G", System.Globalization.CultureInfo.InvariantCulture);
        if (v is double dv)                         return dv.ToString("G", System.Globalization.CultureInfo.InvariantCulture);
        if (v is int iv)                            return iv.ToString();
        if (v is long lv)                           return lv.ToString();
        if (v is Dictionary<string, object> nested) return DictToJson(nested);
        return $"\"{v}\"";
    }

    public static Dictionary<string, string> JsonToDict(string json)
    {
        var result = new Dictionary<string, string>();
        if (string.IsNullOrEmpty(json)) return result;

        json = json.Trim().Trim('{', '}');
        int i = 0;
        while (i < json.Length)
        {
            int ks = json.IndexOf('"', i); if (ks < 0) break; ks++;
            int ke = json.IndexOf('"', ks); if (ke < 0) break;
            string key = json.Substring(ks, ke - ks);

            int col = json.IndexOf(':', ke); if (col < 0) break;
            string rest = json.Substring(col + 1).TrimStart();

            string val;
            int next;
            if (rest.StartsWith("\""))
            {
                int ve = rest.IndexOf('"', 1);
                val  = rest.Substring(1, ve - 1);
                next = col + 1 + rest.IndexOf(',', ve + 1) + 1;
                if (next <= col + 1) next = json.Length;
            }
            else
            {
                int comma = rest.IndexOf(',');
                int brace = rest.IndexOf('}');
                int end   = comma < 0 ? brace : (brace < 0 ? comma : Math.Min(comma, brace));
                val  = end < 0 ? rest.Trim() : rest.Substring(0, end).Trim().Trim('"');
                next = end < 0 ? json.Length : col + 1 + rest.IndexOf(val) + val.Length + 1;
            }

            result[key] = val;
            i = next;
        }
        return result;
    }
}
