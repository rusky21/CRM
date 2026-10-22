using System;
using System.IO;
using System.Threading.Tasks;
using StudioCRM.Core.Enums;
using StudioCRM.Core.Models;
using StudioCRM.Data.Services;
using StudioCRM.Desktop.Services.Http;
using StudioCRM.Desktop.Services.Proxy;
using StudioCRM.Desktop.Services.Settings;
using Xunit;

namespace StudioCRM.Tests;

public class SettingsAndSyncTests
{
    [Fact]
    public void SettingsService_SaveAndLoad_PreservesServerUrlAndMode()
    {
        var settingsService = new SettingsService();
        bool eventFired = false;
        settingsService.ConfigChanged += () => eventFired = true;

        var customConfig = new AppConfig
        {
            Mode = StorageMode.Remote,
            ServerUrl = "http://192.168.1.150:5000",
            TimeoutSeconds = 15
        };

        settingsService.SaveConfig(customConfig);

        Assert.True(eventFired);
        Assert.Equal(StorageMode.Remote, settingsService.CurrentConfig.Mode);
        Assert.Equal("http://192.168.1.150:5000", settingsService.CurrentConfig.ServerUrl);
        Assert.Equal(15, settingsService.CurrentConfig.TimeoutSeconds);

        // Reset to local mode
        settingsService.SaveConfig(new AppConfig { Mode = StorageMode.Local });
        Assert.Equal(StorageMode.Local, settingsService.CurrentConfig.Mode);
    }

    [Fact]
    public void AppConfig_DefaultValues_AreSensible()
    {
        var config = new AppConfig();
        Assert.Equal(StorageMode.Local, config.Mode);
        Assert.Equal("http://127.0.0.1:5000", config.ServerUrl);
        Assert.Equal(10, config.TimeoutSeconds);
    }
}
