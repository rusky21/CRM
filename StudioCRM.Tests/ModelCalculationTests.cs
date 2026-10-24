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

    [Fact]
    public void Order_ManualTotalCost_IsPreservedAndCalculatesDebt()
    {
        var order = new Order
        {
            TotalCost = 150000m, // Set manually, not tied to item sums
            Payments = new List<Payment>
            {
                new() { Amount = 50000m, IsConfirmed = true }
            }
        };

        Assert.Equal(150000m, order.TotalCost);
        Assert.Equal(50000m, order.PaidAmount);
        Assert.Equal(100000m, order.RemainingDebt);
    }

    [Fact]
    public void DateTimeToOffsetConverter_ConvertsBidirectionallyWithoutLoss()
    {
        var converter = StudioCRM.Desktop.Converters.DateTimeToOffsetConverter.Instance;
        var testDate = new DateTime(2026, 10, 8, 0, 0, 0, DateTimeKind.Unspecified);

        // Convert DateTime -> DateTimeOffset?
        var converted = converter.Convert(testDate, typeof(DateTimeOffset?), null, System.Globalization.CultureInfo.InvariantCulture);
        Assert.NotNull(converted);
        Assert.IsType<DateTimeOffset>(converted);
        var offset = (DateTimeOffset)converted;
        Assert.Equal(2026, offset.Year);
        Assert.Equal(10, offset.Month);
        Assert.Equal(8, offset.Day);

        // ConvertBack DateTimeOffset? -> DateTime?
        var convertedBack = converter.ConvertBack(offset, typeof(DateTime?), null, System.Globalization.CultureInfo.InvariantCulture);
        Assert.NotNull(convertedBack);
        Assert.IsType<DateTime>(convertedBack);
        var backDate = (DateTime)convertedBack;
        Assert.Equal(testDate, backDate);
    }

    [Fact]
    public void Order_EmptyItemsAndPayments_HasZeroTotals()
    {
        var order = new Order();
        Assert.Equal(0m, order.TotalCost);
        Assert.Equal(0m, order.PaidAmount);
        Assert.Equal(0m, order.RemainingDebt);
        Assert.Equal(0, order.ProgressPercentage);
    }

    [Fact]
    public void Order_ProgressPercentage_CalculatesBasedOnStages()
    {
        var order = new Order
        {
            Stages = new List<OrderStage>
            {
                new() { Title = "Этап 1", Status = "Completed" },
                new() { Title = "Этап 2", Status = "Completed" },
                new() { Title = "Этап 3", Status = "Pending" },
                new() { Title = "Этап 4", Status = "Pending" }
            }
        };

        Assert.Equal(50, order.ProgressPercentage);

        // Complete all
        order.Stages[2].Status = "Completed";
        order.Stages[3].Status = "Completed";
        Assert.Equal(100, order.ProgressPercentage);
    }

    [Fact]
    public void CurrencyFormatConverter_FormatsCorrectly()
    {
        var converter = StudioCRM.Desktop.Converters.CurrencyFormatConverter.Instance;

        var result = converter.Convert(150000m, typeof(string), null, System.Globalization.CultureInfo.InvariantCulture);
        Assert.NotNull(result);
        Assert.Contains("150", result.ToString());
        Assert.Contains("₽", result.ToString());

        var zero = converter.Convert(0m, typeof(string), null, System.Globalization.CultureInfo.InvariantCulture);
        Assert.Equal("0 ₽", zero);

        var nullVal = converter.Convert(null, typeof(string), null, System.Globalization.CultureInfo.InvariantCulture);
        Assert.Equal("0 ₽", nullVal);
    }

    [Fact]
    public void OrderStatusToStringConverter_TranslatesAllStatuses()
    {
        var converter = StudioCRM.Desktop.Converters.OrderStatusToStringConverter.Instance;

        Assert.Equal("Новый", converter.Convert(OrderStatus.New, typeof(string), null, System.Globalization.CultureInfo.InvariantCulture));
        Assert.Equal("В работе", converter.Convert(OrderStatus.InProgress, typeof(string), null, System.Globalization.CultureInfo.InvariantCulture));
        Assert.Equal("Тестирование", converter.Convert(OrderStatus.Testing, typeof(string), null, System.Globalization.CultureInfo.InvariantCulture));
        Assert.Equal("Сдан", converter.Convert(OrderStatus.Completed, typeof(string), null, System.Globalization.CultureInfo.InvariantCulture));
        Assert.Equal("Отменен", converter.Convert(OrderStatus.Cancelled, typeof(string), null, System.Globalization.CultureInfo.InvariantCulture));
    }

    [Fact]
    public void PaymentTypeToStringConverter_TranslatesAllPaymentTypes()
    {
        var converter = StudioCRM.Desktop.Converters.PaymentTypeToStringConverter.Instance;

        Assert.Equal("Безналичный (Р/С)", converter.Convert(PaymentType.BankTransfer, typeof(string), null, System.Globalization.CultureInfo.InvariantCulture));
        Assert.Equal("Банковская карта", converter.Convert(PaymentType.Card, typeof(string), null, System.Globalization.CultureInfo.InvariantCulture));
        Assert.Equal("Наличные", converter.Convert(PaymentType.Cash, typeof(string), null, System.Globalization.CultureInfo.InvariantCulture));
        Assert.Equal("Криптовалюта (USDT)", converter.Convert(PaymentType.Crypto, typeof(string), null, System.Globalization.CultureInfo.InvariantCulture));
    }
}
