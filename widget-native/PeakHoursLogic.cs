using System;

namespace ClaudePeakWidget;

/// <summary>Peak hours status.</summary>
public enum PeakStatus { OffPeak, Peak, Warning }

/// <summary>Snapshot of the current peak-hours state.</summary>
public record PeakState(
    bool IsPeak,
    PeakStatus Status,
    double SecondsUntilChange,
    string CountdownText,
    string PeakHoursLocal,
    string NextChangeLabel,
    string StatusTitle,
    string StatusDescription,
    string StatusColor
);

/// <summary>
/// Pure clock-based logic — zero API calls.
/// Peak hours: weekdays 5:00–11:00 AM Pacific Time.
/// </summary>
public static class PeakHoursLogic
{
    private static readonly TimeZoneInfo PT =
        TimeZoneInfo.FindSystemTimeZoneById("Pacific Standard Time");

    private const int PeakStartHour = 5;
    private const int PeakEndHour = 11;
    private const double WarningSeconds = 15 * 60;

    private static readonly bool IsPolish =
        System.Globalization.CultureInfo.CurrentUICulture.TwoLetterISOLanguageName == "pl";

    public static PeakState GetState()
    {
        var utcNow = DateTimeOffset.UtcNow;
        var ptNow = TimeZoneInfo.ConvertTime(utcNow, PT);

        var weekday = ptNow.DayOfWeek; // Sunday=0
        bool isWeekday = weekday >= DayOfWeek.Monday && weekday <= DayOfWeek.Friday;
        int hour = ptNow.Hour, minute = ptNow.Minute, second = ptNow.Second;
        bool isPeak = isWeekday && hour >= PeakStartHour && hour < PeakEndHour;

        double secIntoDay = hour * 3600 + minute * 60 + second;
        double peakStartSec = PeakStartHour * 3600;
        double peakEndSec = PeakEndHour * 3600;

        double secs;
        bool nextIsPeak;

        if (!isWeekday)
        {
            int daysUntilMonday = weekday == DayOfWeek.Sunday ? 1 : (8 - (int)weekday);
            secs = daysUntilMonday * 86400 - secIntoDay + peakStartSec;
            nextIsPeak = true;
        }
        else if (isPeak)
        {
            secs = peakEndSec - secIntoDay;
            nextIsPeak = false;
        }
        else if (secIntoDay < peakStartSec)
        {
            secs = peakStartSec - secIntoDay;
            nextIsPeak = true;
        }
        else
        {
            if (weekday == DayOfWeek.Friday)
                secs = 2 * 86400 + (86400 - secIntoDay) + peakStartSec;
            else
                secs = (86400 - secIntoDay) + peakStartSec;
            nextIsPeak = true;
        }

        secs = Math.Max(0, secs);

        var status = secs <= WarningSeconds ? PeakStatus.Warning
                   : isPeak ? PeakStatus.Peak
                   : PeakStatus.OffPeak;

        string peakLocal = ComputeLocalPeakHours();

        string nextLabel = isPeak
            ? (IsPolish ? "Pełna moc za" : "Full power in")
            : (IsPolish ? "Ograniczenia za" : "Higher usage in");

        string title = isPeak
            ? (IsPolish ? "ZWIĘKSZONE ZUŻYCIE" : "HIGHER USAGE")
            : (IsPolish ? "PEŁNA MOC" : "FULL POWER");

        string desc = isPeak
            ? (IsPolish ? "Limity zużywają się szybciej" : "Limits consumed faster")
            : (IsPolish ? "Claude działa na full — korzystaj!" : "Claude at full capacity — go ahead!");

        string color = status switch
        {
            PeakStatus.OffPeak => "Good",
            PeakStatus.Peak => "Attention",
            PeakStatus.Warning => "Warning",
            _ => "Default"
        };

        return new PeakState(
            IsPeak: isPeak,
            Status: status,
            SecondsUntilChange: secs,
            CountdownText: FormatCountdown(secs),
            PeakHoursLocal: peakLocal,
            NextChangeLabel: nextLabel,
            StatusTitle: title,
            StatusDescription: desc,
            StatusColor: color
        );
    }

    private static string FormatCountdown(double seconds)
    {
        int totalMinutes = (int)(seconds / 60);
        int hours = totalMinutes / 60;
        int minutes = totalMinutes % 60;

        if (hours > 24)
        {
            int days = hours / 24;
            int rem = hours % 24;
            return $"{days}d {rem}h";
        }
        return hours > 0 ? $"{hours}h {minutes}min" : $"{minutes}min";
    }

    private static string ComputeLocalPeakHours()
    {
        var today = DateTime.Today;
        var startPt = new DateTime(today.Year, today.Month, today.Day, PeakStartHour, 0, 0);
        var endPt = new DateTime(today.Year, today.Month, today.Day, PeakEndHour, 0, 0);

        var startUtc = TimeZoneInfo.ConvertTimeToUtc(startPt, PT);
        var endUtc = TimeZoneInfo.ConvertTimeToUtc(endPt, PT);

        var startLocal = startUtc.ToLocalTime();
        var endLocal = endUtc.ToLocalTime();

        var tz = TimeZoneInfo.Local.StandardName;
        // Use abbreviation if possible
        if (tz.Contains(' '))
            tz = string.Concat(tz.Split(' ').Select(w => w[0]));

        return $"{startLocal:HH:mm}–{endLocal:HH:mm} {tz}";
    }
}
