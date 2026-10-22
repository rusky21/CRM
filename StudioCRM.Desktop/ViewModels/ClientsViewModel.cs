using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using StudioCRM.Core.Interfaces;
using StudioCRM.Core.Models;

namespace StudioCRM.Desktop.ViewModels;

public partial class ClientsViewModel : ViewModelBase
{
    private readonly IClientService _clientService;

    [ObservableProperty]
    private bool _isLoading;

    [ObservableProperty]
    private string _searchText = string.Empty;

    [ObservableProperty]
    private Client? _selectedClient;

    // Slide-over / Modal editor
    [ObservableProperty]
    private bool _isEditorOpen;

    [ObservableProperty]
    private string _editorTitle = "Новый клиент";

    [ObservableProperty]
    private int _editingClientId;

    [ObservableProperty]
    private string _clientName = string.Empty;

    [ObservableProperty]
    private string? _contactPerson;

    [ObservableProperty]
    private string? _phone;

    [ObservableProperty]
    private string? _email;

    [ObservableProperty]
    private string? _telegram;

    [ObservableProperty]
    private string? _notes;

    [ObservableProperty]
    private string? _statusMessage;

    public ObservableCollection<Client> Clients { get; } = new();
    public ObservableCollection<Client> FilteredClients { get; } = new();

    public ClientsViewModel(IClientService clientService)
    {
        _clientService = clientService;
    }

    public async Task InitializeAsync()
    {
        await LoadClientsAsync();
    }

    [RelayCommand]
    public async Task LoadClientsAsync()
    {
        IsLoading = true;
        try
        {
            var list = await _clientService.GetClientsAsync();
            Clients.Clear();
            foreach (var client in list)
            {
                Clients.Add(client);
            }
            ApplyFilter();
        }
        finally
        {
            IsLoading = false;
        }
    }

    partial void OnSearchTextChanged(string value) => ApplyFilter();

    private void ApplyFilter()
    {
        FilteredClients.Clear();
        var query = Clients.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(SearchText))
        {
            string term = SearchText.Trim().ToLowerInvariant();
            query = query.Where(c =>
                (c.Name?.ToLowerInvariant().Contains(term) ?? false) ||
                (c.ContactPerson?.ToLowerInvariant().Contains(term) ?? false) ||
                (c.Phone?.ToLowerInvariant().Contains(term) ?? false) ||
                (c.Email?.ToLowerInvariant().Contains(term) ?? false) ||
                (c.Telegram?.ToLowerInvariant().Contains(term) ?? false));
        }

        foreach (var c in query)
        {
            FilteredClients.Add(c);
        }
    }

    [RelayCommand]
    public void OpenCreateClient()
    {
        EditorTitle = "Добавление нового клиента";
        EditingClientId = 0;
        ClientName = string.Empty;
        ContactPerson = null;
        Phone = null;
        Email = null;
        Telegram = null;
        Notes = null;
        StatusMessage = null;
        IsEditorOpen = true;
    }

    [RelayCommand]
    public void OpenEditClient(Client? client)
    {
        if (client == null) return;

        EditorTitle = $"Редактирование: {client.Name}";
        EditingClientId = client.Id;
        ClientName = client.Name;
        ContactPerson = client.ContactPerson;
        Phone = client.Phone;
        Email = client.Email;
        Telegram = client.Telegram;
        Notes = client.Notes;
        StatusMessage = null;
        IsEditorOpen = true;
    }

    [RelayCommand]
    public void CloseEditor()
    {
        IsEditorOpen = false;
        StatusMessage = null;
    }

    [RelayCommand]
    public async Task SaveClientAsync()
    {
        if (string.IsNullOrWhiteSpace(ClientName))
        {
            StatusMessage = "Введите название компании или имя клиента.";
            return;
        }

        try
        {
            var client = new Client
            {
                Id = EditingClientId,
                Name = ClientName.Trim(),
                ContactPerson = ContactPerson?.Trim(),
                Phone = Phone?.Trim(),
                Email = Email?.Trim(),
                Telegram = Telegram?.Trim(),
                Notes = Notes?.Trim()
            };

            await _clientService.AddOrUpdateClientAsync(client);
            IsEditorOpen = false;
            await LoadClientsAsync();
        }
        catch (Exception ex)
        {
            StatusMessage = $"Ошибка: {ex.Message}";
        }
    }

    [RelayCommand]
    public async Task DeleteClientAsync(Client? client)
    {
        if (client == null) return;

        try
        {
            await _clientService.DeleteClientAsync(client.Id);
            await LoadClientsAsync();
        }
        catch (Exception ex)
        {
            StatusMessage = ex.Message;
        }
    }
}
