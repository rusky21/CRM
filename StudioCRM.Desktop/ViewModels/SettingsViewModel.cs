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
    private string _serverUrl = "http://127.0.0.1:5000";

    [ObservableProperty]
    private bool _isTesting;

    [ObservableProperty]
    private string? _testResultText;

    [ObservableProperty]
    private bool _isTestSuccess;

    [ObservableProperty]
    private string? _saveMessage;

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
        ServerUrl = config.ServerUrl;
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
            TestResultText = "Укажите IP-адрес или домен сервера.";
            IsTestSuccess = false;
            return;
        }

        // Clean URL
        string url = ServerUrl.Trim();
        if (!url.StartsWith("http://") && !url.StartsWith("https://"))
        {
            url = "http://" + url;
            ServerUrl = url;
        }

        IsTesting = true;
        TestResultText = "Проверка соединения с сервером...";
        try
        {
            // Temporarily update current config in memory to test this URL
            var oldUrl = _settingsService.CurrentConfig.ServerUrl;
            _settingsService.CurrentConfig.ServerUrl = url;

            var (success, message, elapsedMs) = await _apiClient.CheckHealthAsync();
            IsTestSuccess = success;
            TestResultText = message;

            if (!success)
            {
                _settingsService.CurrentConfig.ServerUrl = oldUrl;
            }
        }
        catch (Exception ex)
        {
            IsTestSuccess = false;
            TestResultText = $"Ошибка: {ex.Message}";
        }
        finally
        {
            IsTesting = false;
        }
    }

    [RelayCommand]
    public void SaveSettings()
    {
        string url = ServerUrl.Trim();
        if (!url.StartsWith("http://") && !url.StartsWith("https://"))
        {
            url = "http://" + url;
            ServerUrl = url;
        }

        var newConfig = new AppConfig
        {
            Mode = IsRemoteMode ? StorageMode.Remote : StorageMode.Local,
            ServerUrl = url
        };

        _settingsService.SaveConfig(newConfig);

        SaveMessage = newConfig.Mode == StorageMode.Remote
            ? $"Настройки сохранены! Активен серверный режим ({url})."
            : "Настройки сохранены! Активен локальный режим (SQLite).";

        _onSettingsApplied?.Invoke();
    }
}
