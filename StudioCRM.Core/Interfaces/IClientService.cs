using StudioCRM.Core.Models;

namespace StudioCRM.Core.Interfaces;

public interface IClientService
{
    Task<List<Client>> GetClientsAsync();
    Task<Client?> GetClientByIdAsync(int id);
    Task<Client> AddOrUpdateClientAsync(Client client);
    Task<bool> DeleteClientAsync(int id);
}
