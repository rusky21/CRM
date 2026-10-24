using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using StudioCRM.Core.Enums;
using StudioCRM.Core.Interfaces;
using StudioCRM.Core.Models;

namespace StudioCRM.Desktop.ViewModels;

public partial class ServicesCatalogViewModel : ViewModelBase
{
    private readonly IServiceCatalogService _catalogService;

    [ObservableProperty]
    private bool _isLoading;

    [ObservableProperty]
    private string _searchText = string.Empty;

    [ObservableProperty]
    private string _selectedCategory = "Все";

    [ObservableProperty]
    private ServiceItem? _selectedService;

    // Modal/Slide-over editor
    [ObservableProperty]
    private bool _isEditorOpen;

    [ObservableProperty]
    private string _editorTitle = "Новая услуга";

    [ObservableProperty]
    private int _editingServiceId;

    [ObservableProperty]
    private string _serviceCategory = "Веб-разработка";

    [ObservableProperty]
    private string _serviceTitle = string.Empty;

    [ObservableProperty]
    private BillingType _serviceBillingType = BillingType.Fix;

    [ObservableProperty]
    private decimal _servicePrice = 10000m;

    [ObservableProperty]
    private string _serviceUnit = "проект";

    [ObservableProperty]
    private string? _serviceDescription;

    [ObservableProperty]
    private string? _statusMessage;

    public ObservableCollection<ServiceItem> Services { get; } = new();
    public ObservableCollection<ServiceItem> FilteredServices { get; } = new();
    public ObservableCollection<string> Categories { get; } = new() { "Все" };

    public Array BillingTypes => Enum.GetValues(typeof(BillingType));

    public ServicesCatalogViewModel(IServiceCatalogService catalogService)
    {
        _catalogService = catalogService;
    }

    public async Task InitializeAsync()
    {
        await LoadServicesAsync();
    }

    [RelayCommand]
    public async Task LoadServicesAsync()
    {
        IsLoading = true;
        try
        {
            var list = await _catalogService.GetAllServicesAsync();
            Services.Clear();
            foreach (var item in list)
            {
                Services.Add(item);
            }

            var cats = await _catalogService.GetCategoriesAsync();
            Categories.Clear();
            Categories.Add("Все");
            foreach (var cat in cats)
            {
                Categories.Add(cat);
            }

            ApplyFilter();
        }
        finally
        {
            IsLoading = false;
        }
    }

    partial void OnSearchTextChanged(string value) => ApplyFilter();
    partial void OnSelectedCategoryChanged(string value) => ApplyFilter();

    private void ApplyFilter()
    {
        FilteredServices.Clear();
        var query = Services.AsEnumerable();

        if (SelectedCategory != "Все")
        {
            query = query.Where(s => s.Category == SelectedCategory);
        }

        if (!string.IsNullOrWhiteSpace(SearchText))
        {
            string term = SearchText.Trim().ToLowerInvariant();
            query = query.Where(s =>
                (s.Title?.ToLowerInvariant().Contains(term) ?? false) ||
                (s.Category?.ToLowerInvariant().Contains(term) ?? false) ||
                (s.Description?.ToLowerInvariant().Contains(term) ?? false));
        }

        foreach (var item in query)
        {
            FilteredServices.Add(item);
        }
    }

    [RelayCommand]
    public void OpenCreateService()
    {
        EditorTitle = "Добавление услуги в прайс-лист";
        EditingServiceId = 0;
        ServiceCategory = SelectedCategory != "Все" ? SelectedCategory : "Веб-разработка";
        ServiceTitle = string.Empty;
        ServiceBillingType = BillingType.Fix;
        ServicePrice = 10000m;
        ServiceUnit = "проект";
        ServiceDescription = null;
        StatusMessage = null;
        IsEditorOpen = true;
    }

    [RelayCommand]
    public void OpenEditService(ServiceItem? service)
    {
        if (service == null) return;

        EditorTitle = $"Редактирование: {service.Title}";
        EditingServiceId = service.Id;
        ServiceCategory = service.Category;
        ServiceTitle = service.Title;
        ServiceBillingType = service.BillingType;
        ServicePrice = service.DefaultPrice;
        ServiceUnit = service.Unit;
        ServiceDescription = service.Description;
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
    public async Task SaveServiceAsync()
    {
        if (string.IsNullOrWhiteSpace(ServiceTitle))
        {
            StatusMessage = "Введите название услуги.";
            return;
        }

        try
        {
            var item = new ServiceItem
            {
                Id = EditingServiceId,
                Category = ServiceCategory.Trim(),
                Title = ServiceTitle.Trim(),
                BillingType = ServiceBillingType,
                DefaultPrice = ServicePrice,
                Unit = ServiceUnit.Trim(),
                Description = ServiceDescription?.Trim(),
                IsActive = true
            };

            await _catalogService.SaveServiceAsync(item);
            IsEditorOpen = false;
            await LoadServicesAsync();
        }
        catch (Exception ex)
        {
            StatusMessage = $"Ошибка сохранения: {ex.Message}";
        }
    }

    [RelayCommand]
    public async Task DeleteServiceAsync(ServiceItem? service)
    {
        if (service == null) return;

        try
        {
            await _catalogService.DeleteServiceAsync(service.Id);
            await LoadServicesAsync();
        }
        catch (Exception ex)
        {
            StatusMessage = ex.Message;
        }
    }

    [RelayCommand]
    public async Task UpdateServicePriceAsync(ServiceItem? service)
    {
        if (service == null) return;
        await _catalogService.SaveServiceAsync(service);
    }
}
