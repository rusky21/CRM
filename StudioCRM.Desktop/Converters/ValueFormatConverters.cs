using System;
using System.Globalization;
using Avalonia.Data.Converters;
using Avalonia.Media;
using StudioCRM.Core.Enums;

namespace StudioCRM.Desktop.Converters;

public class OrderStatusToStringConverter : IValueConverter
{
    public static readonly OrderStatusToStringConverter Instance = new();

    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is OrderStatus status)
        {
            return status switch
            {
                OrderStatus.New => "Новый",
                OrderStatus.InProgress => "В работе",
                OrderStatus.Testing => "Тестирование",
                OrderStatus.Completed => "Сдан",
                OrderStatus.Cancelled => "Отменен",
                _ => status.ToString()
            };
        }
        return value?.ToString() ?? "";
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture) => throw new NotImplementedException();
}

public class BillingTypeToStringConverter : IValueConverter
{
    public static readonly BillingTypeToStringConverter Instance = new();

    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is BillingType billing)
        {
            return billing switch
            {
                BillingType.Fix => "Фикс",
                BillingType.Hourly => "Почасовая",
                BillingType.Monthly => "Ежемесячно",
                BillingType.AdBudget => "% бюджета",
                _ => billing.ToString()
            };
        }
        return value?.ToString() ?? "";
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture) => throw new NotImplementedException();
}

public class PaymentTypeToStringConverter : IValueConverter
{
    public static readonly PaymentTypeToStringConverter Instance = new();

    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is PaymentType paymentType)
        {
            return paymentType switch
            {
                PaymentType.BankTransfer => "Безналичный (Р/С)",
                PaymentType.Card => "Банковская карта",
                PaymentType.Cash => "Наличные",
                PaymentType.Crypto => "Криптовалюта (USDT)",
                PaymentType.Other => "Другое",
                _ => paymentType.ToString()
            };
        }
        return value?.ToString() ?? "";
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture) => throw new NotImplementedException();
}

public class CurrencyFormatConverter : IValueConverter
{
    public static readonly CurrencyFormatConverter Instance = new();
    private static readonly CultureInfo RussianCulture = new("ru-RU");

    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is decimal d)
            return $"{d.ToString("#,##0", RussianCulture)} ₽";
        if (value is double dbl)
            return $"{dbl.ToString("#,##0", RussianCulture)} ₽";
        if (value is int i)
            return $"{i.ToString("#,##0", RussianCulture)} ₽";
        return "0 ₽";
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture) => throw new NotImplementedException();
}

public class DebtToBrushConverter : IValueConverter
{
    public static readonly DebtToBrushConverter Instance = new();

    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is decimal debt)
        {
            if (debt > 0)
                return Brush.Parse("#F87171"); // Red / Coral
            return Brush.Parse("#34D399");     // Emerald
        }
        return Brush.Parse("#94A3B8");
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture) => throw new NotImplementedException();
}

public class DateTimeFormatConverter : IValueConverter
{
    public static readonly DateTimeFormatConverter Instance = new();

    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is DateTime dt)
        {
            return dt.ToString("dd.MM.yyyy");
        }
        return "—";
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture) => throw new NotImplementedException();
}
