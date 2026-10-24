using StudioCRM.Core.Models;

namespace StudioCRM.Core.Interfaces;

public interface IServiceCatalogService
{
    Task<List<ServiceItem>> GetAllServicesAsync();
    Task<List<ServiceItem>> GetServicesByCategoryAsync(string? category = null);
    Task<List<string>> GetCategoriesAsync();
    Task<ServiceItem> SaveServiceAsync(ServiceItem service);
    Task<bool> DeleteServiceAsync(int id);
}
