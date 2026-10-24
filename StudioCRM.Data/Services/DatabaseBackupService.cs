using StudioCRM.Core.Interfaces;
using StudioCRM.Data.Context;

namespace StudioCRM.Data.Services;

public class DatabaseBackupService : IDatabaseBackupService
{
    public string GetDatabasePath()
    {
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        string directPath = Path.Combine(baseDir, StudioDbContext.DefaultDbFileName);
        if (File.Exists(directPath))
            return directPath;

        // Also check current working directory
        string cwdPath = Path.Combine(Directory.GetCurrentDirectory(), StudioDbContext.DefaultDbFileName);
        if (File.Exists(cwdPath))
            return cwdPath;

        return directPath;
    }

    public async Task<string> CreateBackupAsync(string? targetDirectory = null)
    {
        string dbPath = GetDatabasePath();
        if (!File.Exists(dbPath))
        {
            // If the file is still newly created in memory or at current directory
            string fallbackPath = Path.GetFullPath(StudioDbContext.DefaultDbFileName);
            if (File.Exists(fallbackPath))
                dbPath = fallbackPath;
            else
                throw new FileNotFoundException("Файл базы данных SQLite не найден для резервного копирования.", dbPath);
        }

        string baseDir = Path.GetDirectoryName(dbPath) ?? AppDomain.CurrentDomain.BaseDirectory;
        string backupsDir = string.IsNullOrWhiteSpace(targetDirectory)
            ? Path.Combine(baseDir, "Backups")
            : targetDirectory;

        if (!Directory.Exists(backupsDir))
        {
            Directory.CreateDirectory(backupsDir);
        }

        string timestamp = DateTime.Now.ToString("yyyy_MM_dd_HHmm");
        string backupFileName = $"backup_{timestamp}.db";
        string backupFilePath = Path.Combine(backupsDir, backupFileName);

        // Ensure unique filename if called within same minute
        int counter = 1;
        while (File.Exists(backupFilePath))
        {
            backupFilePath = Path.Combine(backupsDir, $"backup_{timestamp}_{counter}.db");
            counter++;
        }

        await Task.Run(() =>
        {
            // Open in read share mode so ongoing reads/writes do not block copy
            using var sourceStream = new FileStream(dbPath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
            using var destinationStream = new FileStream(backupFilePath, FileMode.Create, FileAccess.Write, FileShare.None);
            sourceStream.CopyTo(destinationStream);
        });

        return backupFilePath;
    }
}
