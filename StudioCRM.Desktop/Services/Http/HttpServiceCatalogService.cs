using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using StudioCRM.Core.Interfaces;
using StudioCRM.Core.Models;

namespace StudioCRM.Desktop.Services.Http;

public class HttpServiceCatalogService : IServiceCatalogService
{
    private readonly IApiClient _api;

    public HttpServiceCatalogService(IApiClient api)
    {
        _api = api;
    }

    public async Task<List<ServiceItem>> GetAllServicesAsync()
    {
        var result = await _api.GetAsync<List<ServiceItem>>("api/services");
        return result ?? new List<ServiceItem>();
    }

    public async Task<List<ServiceItem>> GetServicesByCategoryAsync(string? category = null)
    {
        string endpoint = string.IsNullOrWhiteSpace(category) || category == "Все"
            ? "api/services"
            : $"api/services/category/{Uri.EscapeDataString(category)}";

        var result = await _api.GetAsync<List<ServiceItem>>(endpoint);
        return result ?? new List<ServiceItem>();
    }

    public async Task<List<string>> GetCategoriesAsync()
    {
        var result = await _api.GetAsync<List<string>>("api/services/categories");
        return result ?? new List<string>();
    }

    public async Task<ServiceItem> SaveServiceAsync(ServiceItem service)
    {
        var result = await _api.PostAsync<ServiceItem, ServiceItem>("api/services", service);
        return result ?? service;
    }

    public async Task<bool> DeleteServiceAsync(int id)
    {
        try
        {
            await _api.DeleteAsync($"api/services/{id}");
            return true;
        }
        catch
        {
            return false;
        }
    }
}
