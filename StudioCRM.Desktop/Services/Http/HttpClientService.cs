using System.Collections.Generic;
using System.Threading.Tasks;
using StudioCRM.Core.Interfaces;
using StudioCRM.Core.Models;

namespace StudioCRM.Desktop.Services.Http;

public class HttpClientService : IClientService
{
    private readonly IApiClient _api;

    public HttpClientService(IApiClient api)
    {
        _api = api;
    }

    public async Task<List<Client>> GetClientsAsync()
    {
        var result = await _api.GetAsync<List<Client>>("api/clients");
        return result ?? new List<Client>();
    }

    public async Task<Client?> GetClientByIdAsync(int id)
    {
        return await _api.GetAsync<Client>($"api/clients/{id}");
    }

    public async Task<Client> AddOrUpdateClientAsync(Client client)
    {
        var result = await _api.PostAsync<Client, Client>("api/clients", client);
        return result ?? client;
    }

    public async Task<bool> DeleteClientAsync(int id)
    {
        try
        {
            await _api.DeleteAsync($"api/clients/{id}");
            return true;
        }
        catch
        {
            return false;
        }
    }
}
