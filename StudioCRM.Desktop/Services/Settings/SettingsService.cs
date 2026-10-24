using System;
using System.IO;
using System.Text.Json;

namespace StudioCRM.Desktop.Services.Settings;

public enum StorageMode
{
    Local,
    Remote
}

public class AppConfig
{
    public StorageMode Mode { get; set; } = StorageMode.Local;
    public string ServerUrl { get; set; } = "http://212.67.15.218:5000";
    public int TimeoutSeconds { get; set; } = 10;
}

public interface ISettingsService
{
    AppConfig CurrentConfig { get; }
    void SaveConfig(AppConfig config);
    event Action? ConfigChanged;
}

public class SettingsService : ISettingsService
{
    public static readonly string AppDataSettingsFilePath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "StudioCRM",
        "settings.json");

    public static readonly string LocalSettingsFilePath = Path.Combine(
        AppDomain.CurrentDomain.BaseDirectory,
        "settings.json");

    public AppConfig CurrentConfig { get; private set; }

    public event Action? ConfigChanged;

    public SettingsService()
    {
        CurrentConfig = LoadConfig();
    }

    /// <summary>
    /// Normalizes server input: trims, adds http:// scheme if missing, and appends default port :5000 for bare IPs/hostnames.
    /// </summary>
    public static string NormalizeServerUrl(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return "http://212.67.15.218:5000";

        string input = raw.Trim().TrimEnd('/');
        bool hasScheme = input.StartsWith("http://", StringComparison.OrdinalIgnoreCase) ||
                         input.StartsWith("https://", StringComparison.OrdinalIgnoreCase);

        if (!hasScheme)
        {
            input = "http://" + input;
        }

        if (Uri.TryCreate(input, UriKind.Absolute, out var uri))
        {
            // If scheme is http, port is default 80, and user did not explicitly enter :80, default to :5000
            if (uri.Scheme.Equals("http", StringComparison.OrdinalIgnoreCase) &&
                uri.Port == 80 &&
                !raw.Contains(":80"))
            {
                var builder = new UriBuilder(uri) { Port = 5000 };
                return builder.Uri.ToString().TrimEnd('/');
            }

            return uri.ToString().TrimEnd('/');
        }

        return input;
    }

    public AppConfig LoadConfig()
    {
        // 1. Try local portable settings.json next to executable first
        try
        {
            if (File.Exists(LocalSettingsFilePath))
            {
                string json = File.ReadAllText(LocalSettingsFilePath);
                var config = JsonSerializer.Deserialize<AppConfig>(json);
                if (config != null)
                {
                    config.ServerUrl = NormalizeServerUrl(config.ServerUrl);
                    return config;
                }
            }
        }
        catch
        {
            // Fall through to AppData
        }

        // 2. Try AppData settings.json
        try
        {
            if (File.Exists(AppDataSettingsFilePath))
            {
                string json = File.ReadAllText(AppDataSettingsFilePath);
                var config = JsonSerializer.Deserialize<AppConfig>(json);
                if (config != null)
                {
                    config.ServerUrl = NormalizeServerUrl(config.ServerUrl);
                    return config;
                }
            }
        }
        catch
        {
            // Fallback to default
        }

        return new AppConfig();
    }

    public void SaveConfig(AppConfig config)
    {
        config.ServerUrl = NormalizeServerUrl(config.ServerUrl);
        CurrentConfig = config;

        string json = JsonSerializer.Serialize(config, new JsonSerializerOptions { WriteIndented = true });

        // 1. Save to AppData
        try
        {
            string dir = Path.GetDirectoryName(AppDataSettingsFilePath)!;
            if (!Directory.Exists(dir))
            {
                Directory.CreateDirectory(dir);
            }
            File.WriteAllText(AppDataSettingsFilePath, json);
        }
        catch
        {
            // Ignore write errors to AppData
        }

        // 2. Save to local application directory for portable use
        try
        {
            File.WriteAllText(LocalSettingsFilePath, json);
        }
        catch
        {
            // Ignore write errors if running from read-only directory
        }

        ConfigChanged?.Invoke();
    }
}
