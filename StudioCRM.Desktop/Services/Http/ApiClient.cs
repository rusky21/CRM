using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading.Tasks;
using StudioCRM.Desktop.Services.Settings;

namespace StudioCRM.Desktop.Services.Http;

public interface IApiClient
{
    HttpClient GetClient();
    Task<T?> GetAsync<T>(string endpoint);
    Task<TResponse?> PostAsync<TRequest, TResponse>(string endpoint, TRequest request);
    Task PostAsync<TRequest>(string endpoint, TRequest request);
    Task<TResponse?> PutAsync<TRequest, TResponse>(string endpoint, TRequest request);
    Task PatchAsync<TRequest>(string endpoint, TRequest request);
    Task DeleteAsync(string endpoint);
    Task<(bool Success, string Message, long ElapsedMs)> CheckHealthAsync();
}

public class ApiClient : IApiClient
{
    private readonly ISettingsService _settingsService;
    private readonly HttpClient _httpClient;
    private readonly JsonSerializerOptions _jsonOptions;

    public ApiClient(ISettingsService settingsService)
    {
        _settingsService = settingsService;
        _httpClient = new HttpClient();
        _jsonOptions = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
        };
        _jsonOptions.Converters.Add(new JsonStringEnumConverter());
    }

    private string GetFullUrl(string endpoint)
    {
        string baseUrl = _settingsService.CurrentConfig.ServerUrl.TrimEnd('/');
        string cleanEndpoint = endpoint.TrimStart('/');
        return $"{baseUrl}/{cleanEndpoint}";
    }

    public HttpClient GetClient() => _httpClient;

    public async Task<T?> GetAsync<T>(string endpoint)
    {
        string url = GetFullUrl(endpoint);
        using var response = await _httpClient.GetAsync(url);
        response.EnsureSuccessStatusCode();

        await using var stream = await response.Content.ReadAsStreamAsync();
        return await JsonSerializer.DeserializeAsync<T>(stream, _jsonOptions);
    }

    public async Task<TResponse?> PostAsync<TRequest, TResponse>(string endpoint, TRequest request)
    {
        string url = GetFullUrl(endpoint);
        string json = JsonSerializer.Serialize(request, _jsonOptions);
        using var content = new StringContent(json, Encoding.UTF8, "application/json");

        using var response = await _httpClient.PostAsync(url, content);
        response.EnsureSuccessStatusCode();

        await using var stream = await response.Content.ReadAsStreamAsync();
        return await JsonSerializer.DeserializeAsync<TResponse>(stream, _jsonOptions);
    }

    public async Task PostAsync<TRequest>(string endpoint, TRequest request)
    {
        string url = GetFullUrl(endpoint);
        string json = JsonSerializer.Serialize(request, _jsonOptions);
        using var content = new StringContent(json, Encoding.UTF8, "application/json");

        using var response = await _httpClient.PostAsync(url, content);
        response.EnsureSuccessStatusCode();
    }

    public async Task<TResponse?> PutAsync<TRequest, TResponse>(string endpoint, TRequest request)
    {
        string url = GetFullUrl(endpoint);
        string json = JsonSerializer.Serialize(request, _jsonOptions);
        using var content = new StringContent(json, Encoding.UTF8, "application/json");

        using var response = await _httpClient.PutAsync(url, content);
        response.EnsureSuccessStatusCode();

        await using var stream = await response.Content.ReadAsStreamAsync();
        return await JsonSerializer.DeserializeAsync<TResponse>(stream, _jsonOptions);
    }

    public async Task PatchAsync<TRequest>(string endpoint, TRequest request)
    {
        string url = GetFullUrl(endpoint);
        string json = JsonSerializer.Serialize(request, _jsonOptions);
        using var content = new StringContent(json, Encoding.UTF8, "application/json");

        using var requestMessage = new HttpRequestMessage(HttpMethod.Patch, url) { Content = content };
        using var response = await _httpClient.SendAsync(requestMessage);
        response.EnsureSuccessStatusCode();
    }

    public async Task DeleteAsync(string endpoint)
    {
        string url = GetFullUrl(endpoint);
        using var response = await _httpClient.DeleteAsync(url);
        response.EnsureSuccessStatusCode();
    }

    public async Task<(bool Success, string Message, long ElapsedMs)> CheckHealthAsync()
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        try
        {
            string url = GetFullUrl("api/health");
            using var cts = new System.Threading.CancellationTokenSource(TimeSpan.FromSeconds(5));
            using var response = await _httpClient.GetAsync(url, cts.Token);
            sw.Stop();

            if (response.IsSuccessStatusCode)
            {
                string json = await response.Content.ReadAsStringAsync();
                return (true, $"Подключение успешно! ({sw.ElapsedMilliseconds} мс)", sw.ElapsedMilliseconds);
            }

            return (false, $"Сервер вернул код {response.StatusCode} ({sw.ElapsedMilliseconds} мс)", sw.ElapsedMilliseconds);
        }
        catch (Exception ex)
        {
            sw.Stop();
            return (false, $"Ошибка подключения: {ex.Message}", sw.ElapsedMilliseconds);
        }
    }
}
