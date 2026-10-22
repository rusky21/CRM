using Microsoft.EntityFrameworkCore;
using StudioCRM.Core.Interfaces;
using StudioCRM.Core.Models;
using StudioCRM.Data.Context;

namespace StudioCRM.Data.Services;

public class ServiceCatalogService : IServiceCatalogService
{
    private readonly IDbContextFactory<StudioDbContext>? _contextFactory;
    private readonly StudioDbContext _context;

    public ServiceCatalogService(StudioDbContext context, IDbContextFactory<StudioDbContext>? contextFactory = null)
    {
        _context = context;
        _contextFactory = contextFactory;
    }

    public async Task<List<ServiceItem>> GetAllServicesAsync()
    {
        await using var ctx = _contextFactory != null ? await _contextFactory.CreateDbContextAsync() : null;
        var context = ctx ?? _context;

        return await context.ServiceItems
            .AsNoTracking()
            .Where(s => s.IsActive)
            .OrderBy(s => s.Category)
            .ThenBy(s => s.Title)
            .ToListAsync();
    }

    public async Task<List<ServiceItem>> GetServicesByCategoryAsync(string? category = null)
    {
        await using var ctx = _contextFactory != null ? await _contextFactory.CreateDbContextAsync() : null;
        var context = ctx ?? _context;

        var query = context.ServiceItems.AsNoTracking().Where(s => s.IsActive);
        if (!string.IsNullOrWhiteSpace(category) && category != "Все")
        {
            query = query.Where(s => s.Category == category);
        }

        return await query.OrderBy(s => s.Category).ThenBy(s => s.Title).ToListAsync();
    }

    public async Task<List<string>> GetCategoriesAsync()
    {
        await using var ctx = _contextFactory != null ? await _contextFactory.CreateDbContextAsync() : null;
        var context = ctx ?? _context;

        return await context.ServiceItems
            .AsNoTracking()
            .Select(s => s.Category)
            .Distinct()
            .OrderBy(c => c)
            .ToListAsync();
    }

    public async Task<ServiceItem> SaveServiceAsync(ServiceItem service)
    {
        await using var ctx = _contextFactory != null ? await _contextFactory.CreateDbContextAsync() : null;
        var context = ctx ?? _context;

        if (service.Id == 0)
        {
            context.ServiceItems.Add(service);
        }
        else
        {
            var existing = await context.ServiceItems.FindAsync(service.Id);
            if (existing != null)
            {
                existing.Category = service.Category;
                existing.Title = service.Title;
                existing.BillingType = service.BillingType;
                existing.DefaultPrice = service.DefaultPrice;
                existing.Unit = service.Unit;
                existing.Description = service.Description;
                existing.IsActive = service.IsActive;
            }
            else
            {
                context.ServiceItems.Update(service);
            }
        }

        await context.SaveChangesAsync();
        return service;
    }

    public async Task<bool> DeleteServiceAsync(int id)
    {
        await using var ctx = _contextFactory != null ? await _contextFactory.CreateDbContextAsync() : null;
        var context = ctx ?? _context;

        var service = await context.ServiceItems.FindAsync(id);
        if (service == null)
            return false;

        // Soft delete to preserve past order item relations
        service.IsActive = false;
        await context.SaveChangesAsync();
        return true;
    }
}
