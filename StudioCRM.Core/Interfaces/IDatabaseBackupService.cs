namespace StudioCRM.Core.Interfaces;

public interface IDatabaseBackupService
{
    Task<string> CreateBackupAsync(string? targetDirectory = null);
    string GetDatabasePath();
}
