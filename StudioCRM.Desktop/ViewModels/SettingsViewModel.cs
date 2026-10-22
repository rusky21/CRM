using System;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using StudioCRM.Desktop.Services.Http;
using StudioCRM.Desktop.Services.Settings;

namespace StudioCRM.Desktop.ViewModels;

public partial class SettingsViewModel : ViewModelBase
{
    private readonly ISettingsService _settingsService;
    private readonly IApiClient _apiClient;
    private readonly Action? _onSettingsApplied;

    [ObservableProperty]
    private bool _isRemoteMode;

    [ObservableProperty]
    private bool _isLocalMode = true;

    [ObservableProperty]
    private string _serverUrl = "http://212.67.15.218:5000";

    [ObservableProperty]
    private bool _isTesting;

    [ObservableProperty]
    private string? _testResultText;

    [ObservableProperty]
    private bool _isTestSuccess;

    [ObservableProperty]
    private string? _saveMessage;

    [ObservableProperty]
    private string _currentSavedServerUrl = "";

    [ObservableProperty]
    private string _currentStorageModeText = "";

    public string SettingsFilesInfo => $"Конфигурация сохраняется в:\n• {SettingsService.LocalSettingsFilePath} (портативный)\n• {SettingsService.AppDataSettingsFilePath}";

    public SettingsViewModel(ISettingsService settingsService, IApiClient apiClient, Action? onSettingsApplied = null)
    {
        _settingsService = settingsService;
        _apiClient = apiClient;
        _onSettingsApplied = onSettingsApplied;

        LoadCurrentSettings();
    }

    private void LoadCurrentSettings()
    {
        var config = _settingsService.CurrentConfig;
        IsRemoteMode = config.Mode == StorageMode.Remote;
        IsLocalMode = config.Mode == StorageMode.Local;
        ServerUrl = SettingsService.NormalizeServerUrl(config.ServerUrl);
        UpdateStatusInfo();
    }

    private void UpdateStatusInfo()
    {
        CurrentSavedServerUrl = _settingsService.CurrentConfig.ServerUrl;
        CurrentStorageModeText = _settingsService.CurrentConfig.Mode == StorageMode.Remote
            ? "🌐 Сетевой сервер (PostgreSQL)"
            : "💻 Локальный (SQLite)";
    }

    [RelayCommand]
    public void SelectLocalMode()
    {
        IsLocalMode = true;
        IsRemoteMode = false;
    }

    [RelayCommand]
    public void SelectRemoteMode()
    {
        IsLocalMode = false;
        IsRemoteMode = true;
    }

    [RelayCommand]
    public void SetStudioServerPreset()
    {
        ServerUrl = "http://212.67.15.218:5000";
    }

    [RelayCommand]
    public void SetLocalhostPreset()
    {
        ServerUrl = "http://127.0.0.1:5000";
    }

    [RelayCommand]
    public void SetLanPreset()
    {
        ServerUrl = "http://192.168.1.100:5000";
    }

    [RelayCommand]
    public async Task TestConnectionAsync()
    {
        if (string.IsNullOrWhiteSpace(ServerUrl))
        {
            TestResultText = "❌ Укажите IP-адрес или домен сервера.";
            IsTestSuccess = false;
            return;
        }

        string url = SettingsService.NormalizeServerUrl(ServerUrl);
        ServerUrl = url;

        IsTesting = true;
        TestResultText = $"Проверка соединения с {url}...";
        try
        {
            var oldUrl = _settingsService.CurrentConfig.ServerUrl;
            _settingsService.CurrentConfig.ServerUrl = url;

            var (success, message, elapsedMs) = await _apiClient.CheckHealthAsync();
            IsTestSuccess = success;
            TestResultText = success
                ? $"✅ Подключение успешно! ({url}, отклик {elapsedMs} мс)"
                : $"❌ Сервер недоступен: {message}";

            if (!success)
            {
                _settingsService.CurrentConfig.ServerUrl = oldUrl;
            }
        }
        catch (Exception ex)
        {
            IsTestSuccess = false;
            TestResultText = $"❌ Ошибка соединения: {ex.Message}";
        }
        finally
        {
            IsTesting = false;
        }
    }

    [RelayCommand]
    public void SaveAndConnectRemote()
    {
        string url = SettingsService.NormalizeServerUrl(ServerUrl);
        ServerUrl = url;
        IsRemoteMode = true;
        IsLocalMode = false;

        var newConfig = new AppConfig
        {
            Mode = StorageMode.Remote,
            ServerUrl = url
        };

        _settingsService.SaveConfig(newConfig);
        UpdateStatusInfo();

        SaveMessage = $"✅ IP сервера сохранен: {url}! Сетевой режим успешно активирован.";
        _onSettingsApplied?.Invoke();
    }

    [RelayCommand]
    public void SaveSettings()
    {
        string url = SettingsService.NormalizeServerUrl(ServerUrl);
        ServerUrl = url;

        var newConfig = new AppConfig
        {
            Mode = IsRemoteMode ? StorageMode.Remote : StorageMode.Local,
            ServerUrl = url
        };

        _settingsService.SaveConfig(newConfig);
        UpdateStatusInfo();

        SaveMessage = newConfig.Mode == StorageMode.Remote
            ? $"✅ Настройки сохранены! Активен серверный режим ({url})."
            : "✅ Настройки сохранены! Активен локальный режим (SQLite).";

        _onSettingsApplied?.Invoke();
    }
}
