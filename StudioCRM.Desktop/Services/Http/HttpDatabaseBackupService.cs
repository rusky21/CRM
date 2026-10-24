using System;
using System.Threading.Tasks;
using StudioCRM.Core.Interfaces;
using StudioCRM.Desktop.Services.Settings;

namespace StudioCRM.Desktop.Services.Http;

public class HttpDatabaseBackupService : IDatabaseBackupService
{
    private readonly IApiClient _api;
    private readonly ISettingsService _settingsService;

    public HttpDatabaseBackupService(IApiClient api, ISettingsService settingsService)
    {
        _api = api;
        _settingsService = settingsService;
    }

    public string GetDatabasePath()
    {
        return $"[Удаленный сервер] {_settingsService.CurrentConfig.ServerUrl}";
    }

    public async Task<string> CreateBackupAsync(string? targetDirectory = null)
    {
        var response = await _api.PostAsync<object, BackupResponse>("api/finances/backup", new { });
        return response?.BackupPath ?? "Резервная копия успешно создана на сервере.";
    }

    private class BackupResponse
    {
        public string? BackupPath { get; set; }
        public DateTime CreatedAt { get; set; }
    }
}
