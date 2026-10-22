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
    public string ServerUrl { get; set; } = "http://127.0.0.1:5000";
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
    private static readonly string SettingsFilePath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "StudioCRM",
        "settings.json");

    public AppConfig CurrentConfig { get; private set; }

    public event Action? ConfigChanged;

    public SettingsService()
    {
        CurrentConfig = LoadConfig();
    }

    public AppConfig LoadConfig()
    {
        try
        {
            if (File.Exists(SettingsFilePath))
            {
                string json = File.ReadAllText(SettingsFilePath);
                var config = JsonSerializer.Deserialize<AppConfig>(json);
                if (config != null)
                {
                    return config;
                }
            }
        }
        catch
        {
            // Fallback to default config on error
        }

        return new AppConfig();
    }

    public void SaveConfig(AppConfig config)
    {
        CurrentConfig = config;
        try
        {
            string dir = Path.GetDirectoryName(SettingsFilePath)!;
            if (!Directory.Exists(dir))
            {
                Directory.CreateDirectory(dir);
            }

            string json = JsonSerializer.Serialize(config, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(SettingsFilePath, json);
        }
        catch
        {
            // Ignore write errors to disk
        }

        ConfigChanged?.Invoke();
    }
}
