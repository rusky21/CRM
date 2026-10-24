using System.Collections.Generic;
using System.Threading.Tasks;
using StudioCRM.Core.Enums;
using StudioCRM.Core.Interfaces;
using StudioCRM.Core.Models;

namespace StudioCRM.Desktop.Services.Http;

public class HttpOrderService : IOrderService
{
    private readonly IApiClient _api;

    public HttpOrderService(IApiClient api)
    {
        _api = api;
    }

    public async Task<List<Order>> GetOrdersSummaryAsync()
    {
        var result = await _api.GetAsync<List<Order>>("api/orders/summary");
        return result ?? new List<Order>();
    }

    public async Task<Order?> GetOrderByIdWithDetailsAsync(int id)
    {
        return await _api.GetAsync<Order>($"api/orders/{id}");
    }

    public async Task<Order> CreateOrderAsync(Order order)
    {
        var result = await _api.PostAsync<Order, Order>("api/orders", order);
        return result ?? order;
    }

    public async Task<Order> UpdateOrderAsync(Order order)
    {
        var result = await _api.PutAsync<Order, Order>($"api/orders/{order.Id}", order);
        return result ?? order;
    }

    public async Task<bool> UpdateOrderStatusAsync(int orderId, OrderStatus newStatus)
    {
        try
        {
            await _api.PatchAsync($"api/orders/{orderId}/status", new { status = newStatus });
            return true;
        }
        catch
        {
            return false;
        }
    }

    public async Task<Payment> AddPaymentAsync(int orderId, Payment payment)
    {
        var result = await _api.PostAsync<Payment, Payment>($"api/orders/{orderId}/payments", payment);
        return result ?? payment;
    }

    public async Task<bool> DeleteOrderAsync(int id)
    {
        try
        {
            await _api.DeleteAsync($"api/orders/{id}");
            return true;
        }
        catch
        {
            return false;
        }
    }
}
