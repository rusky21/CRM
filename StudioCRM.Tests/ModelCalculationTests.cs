using System;
using System.Collections.Generic;
using StudioCRM.Core.Enums;
using StudioCRM.Core.Models;
using Xunit;

namespace StudioCRM.Tests;

public class ModelCalculationTests
{
    [Fact]
    public void Order_CalculatedProperties_ReflectItemsAndPaymentsAccurately()
    {
        // Arrange
        var order = new Order
        {
            OrderNumber = "ORD-TEST-001",
            Title = "Тестовый проект",
            Items = new List<OrderItem>
            {
                new() { Title = "Разработка лендинга", Price = 50000m, Quantity = 1m, Subtotal = 50000m },
                new() { Title = "Интеграция CRM", Price = 2500m, Quantity = 20m, Subtotal = 50000m }
            },
            Payments = new List<Payment>
            {
                new() { Amount = 30000m, IsConfirmed = true, PaymentType = PaymentType.BankTransfer },
                new() { Amount = 20000m, IsConfirmed = true, PaymentType = PaymentType.Card },
                new() { Amount = 15000m, IsConfirmed = false, PaymentType = PaymentType.BankTransfer } // Not confirmed
            }
        };

        // Act
        order.TotalCost = order.Items.Sum(i => i.Subtotal);

        // Assert
        Assert.Equal(100000m, order.TotalCost);
        Assert.Equal(50000m, order.PaidAmount); // Only confirmed payments
        Assert.Equal(50000m, order.RemainingDebt);
    }

    [Fact]
    public void Order_WhenOverpaid_RemainingDebtIsZero()
    {
        // Arrange
        var order = new Order
        {
            TotalCost = 50000m,
            Payments = new List<Payment>
            {
                new() { Amount = 60000m, IsConfirmed = true }
            }
        };

        // Assert
        Assert.Equal(60000m, order.PaidAmount);
        Assert.Equal(0m, order.RemainingDebt);
    }
}
