using Microsoft.EntityFrameworkCore;
using StudioCRM.Core.Interfaces;
using StudioCRM.Core.Models;
using StudioCRM.Data.Context;

namespace StudioCRM.Data.Services;

public class ClientService : IClientService
{
    private readonly IDbContextFactory<StudioDbContext>? _contextFactory;
    private readonly StudioDbContext _context;

    public ClientService(StudioDbContext context, IDbContextFactory<StudioDbContext>? contextFactory = null)
    {
        _context = context;
        _contextFactory = contextFactory;
    }

    private StudioDbContext CreateContext() => _contextFactory?.CreateDbContext() ?? _context;

    public async Task<List<Client>> GetClientsAsync()
    {
        await using var ctx = _contextFactory != null ? await _contextFactory.CreateDbContextAsync() : null;
        var context = ctx ?? _context;

        return await context.Clients
            .AsNoTracking()
            .Include(c => c.Orders)
            .OrderByDescending(c => c.CreatedAt)
            .ToListAsync();
    }

    public async Task<Client?> GetClientByIdAsync(int id)
    {
        await using var ctx = _contextFactory != null ? await _contextFactory.CreateDbContextAsync() : null;
        var context = ctx ?? _context;

        return await context.Clients
            .AsNoTracking()
            .Include(c => c.Orders)
            .FirstOrDefaultAsync(c => c.Id == id);
    }

    public async Task<Client> AddOrUpdateClientAsync(Client client)
    {
        await using var ctx = _contextFactory != null ? await _contextFactory.CreateDbContextAsync() : null;
        var context = ctx ?? _context;

        if (client.Id == 0)
        {
            client.CreatedAt = DateTime.Now;
            context.Clients.Add(client);
        }
        else
        {
            var existing = await context.Clients.FindAsync(client.Id);
            if (existing != null)
            {
                existing.Name = client.Name;
                existing.ContactPerson = client.ContactPerson;
                existing.Phone = client.Phone;
                existing.Email = client.Email;
                existing.Telegram = client.Telegram;
                existing.Notes = client.Notes;
            }
            else
            {
                context.Clients.Update(client);
            }
        }

        await context.SaveChangesAsync();
        return client;
    }

    public async Task<bool> DeleteClientAsync(int id)
    {
        await using var ctx = _contextFactory != null ? await _contextFactory.CreateDbContextAsync() : null;
        var context = ctx ?? _context;

        var client = await context.Clients.Include(c => c.Orders).FirstOrDefaultAsync(c => c.Id == id);
        if (client == null)
            return false;

        if (client.Orders.Any())
        {
            throw new InvalidOperationException("Нельзя удалить клиента, у которого есть привязанные заказы.");
        }

        context.Clients.Remove(client);
        await context.SaveChangesAsync();
        return true;
    }
}
