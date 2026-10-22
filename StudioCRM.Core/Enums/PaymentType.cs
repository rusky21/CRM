namespace StudioCRM.Core.Enums;

public enum PaymentType
{
    BankTransfer = 0,   // Безналичный расчет (Р/С)
    Card = 1,           // Банковская карта
    Cash = 2,           // Наличные
    Crypto = 3,         // Криптовалюта (USDT)
    Other = 4           // Другое
}
