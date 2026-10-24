using System;
using System.Globalization;
using Avalonia.Data.Converters;
using Avalonia.Media;
using StudioCRM.Core.Enums;

namespace StudioCRM.Desktop.Converters;

public class OrderStatusToBrushConverter : IValueConverter
{
    public static readonly OrderStatusToBrushConverter Instance = new();

    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is OrderStatus status)
        {
            return status switch
            {
                OrderStatus.New => Brush.Parse("#3B82F6"),        // Blue
                OrderStatus.InProgress => Brush.Parse("#8B5CF6"), // Purple / Indigo
                OrderStatus.Testing => Brush.Parse("#F59E0B"),    // Amber
                OrderStatus.Completed => Brush.Parse("#10B981"),  // Emerald
                OrderStatus.Cancelled => Brush.Parse("#EF4444"),  // Red
                _ => Brush.Parse("#64748B")
            };
        }
        return Brush.Parse("#64748B");
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture) => throw new NotImplementedException();
}

public class OrderStatusToBackgroundBrushConverter : IValueConverter
{
    public static readonly OrderStatusToBackgroundBrushConverter Instance = new();

    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is OrderStatus status)
        {
            return status switch
            {
                OrderStatus.New => Brush.Parse("#1E3A8A"),        // Dark blue bg
                OrderStatus.InProgress => Brush.Parse("#4C1D95"), // Dark purple bg
                OrderStatus.Testing => Brush.Parse("#78350F"),    // Dark amber bg
                OrderStatus.Completed => Brush.Parse("#064E3B"),  // Dark green bg
                OrderStatus.Cancelled => Brush.Parse("#7F1D1D"),  // Dark red bg
                _ => Brush.Parse("#1E293B")
            };
        }
        return Brush.Parse("#1E293B");
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture) => throw new NotImplementedException();
}
