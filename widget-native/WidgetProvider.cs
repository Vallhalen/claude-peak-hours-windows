using System.Text.Json;
using Microsoft.Windows.Widgets.Providers;

namespace ClaudePeakWidget;

/// <summary>
/// COM-activated Widget Provider for Windows 11 Widget Board.
/// Serves a single widget: "ClaudePeakHours".
/// </summary>
public class WidgetProvider : IWidgetProvider
{
    private const string WidgetId = "ClaudePeakHours";

    // Adaptive Card template with data binding
    private static readonly string CardTemplate = """
    {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.6",
        "body": [
            {
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "width": "auto",
                        "verticalContentAlignment": "Center",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": "${emoji}",
                                "size": "Large"
                            }
                        ]
                    },
                    {
                        "type": "Column",
                        "width": "stretch",
                        "verticalContentAlignment": "Center",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": "${statusTitle}",
                                "weight": "Bolder",
                                "size": "Medium",
                                "color": "${statusColor}",
                                "wrap": false
                            }
                        ]
                    }
                ]
            },
            {
                "type": "TextBlock",
                "text": "${statusDescription}",
                "size": "Small",
                "isSubtle": true,
                "wrap": true,
                "spacing": "Small"
            },
            {
                "type": "ColumnSet",
                "spacing": "Medium",
                "separator": true,
                "columns": [
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": "${nextChangeLabel}",
                                "size": "Small",
                                "isSubtle": true
                            }
                        ]
                    },
                    {
                        "type": "Column",
                        "width": "auto",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": "${countdown}",
                                "size": "Small",
                                "weight": "Bolder"
                            }
                        ]
                    }
                ]
            },
            {
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": "Peak hours",
                                "size": "Small",
                                "isSubtle": true
                            }
                        ]
                    },
                    {
                        "type": "Column",
                        "width": "auto",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": "${peakHoursLocal}",
                                "size": "Small",
                                "weight": "Bolder"
                            }
                        ]
                    }
                ]
            },
            {
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": "${workdaysLabel}",
                                "size": "Small",
                                "isSubtle": true
                            }
                        ]
                    },
                    {
                        "type": "Column",
                        "width": "auto",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": "${workdaysValue}",
                                "size": "Small",
                                "weight": "Bolder"
                            }
                        ]
                    }
                ]
            }
        ]
    }
    """;

    private readonly HashSet<string> _activeWidgets = new();
    private Timer? _updateTimer;

    public WidgetProvider()
    {
        // Update every 60 seconds
        _updateTimer = new Timer(_ => UpdateAllWidgets(), null,
                                  TimeSpan.Zero, TimeSpan.FromSeconds(60));
    }

    public void CreateWidget(WidgetContext widgetContext)
    {
        _activeWidgets.Add(widgetContext.Id);
        UpdateWidget(widgetContext.Id);
    }

    public void DeleteWidget(string widgetId, string customState)
    {
        _activeWidgets.Remove(widgetId);
    }

    public void OnActionInvoked(WidgetActionInvokedArgs actionInvokedArgs)
    {
        // No actions defined — widget is read-only
    }

    public void OnWidgetContextChanged(WidgetContextChangedArgs contextChangedArgs)
    {
        UpdateWidget(contextChangedArgs.WidgetContext.Id);
    }

    public void Activate(WidgetContext widgetContext)
    {
        _activeWidgets.Add(widgetContext.Id);
        UpdateWidget(widgetContext.Id);
    }

    public void Deactivate(string widgetId)
    {
        _activeWidgets.Remove(widgetId);
    }

    private void UpdateAllWidgets()
    {
        foreach (var id in _activeWidgets.ToArray())
        {
            UpdateWidget(id);
        }
    }

    private void UpdateWidget(string widgetId)
    {
        try
        {
            var state = PeakHoursLogic.GetState();
            bool isPolish = System.Globalization.CultureInfo.CurrentUICulture
                .TwoLetterISOLanguageName == "pl";

            var data = new
            {
                emoji = state.Status switch
                {
                    PeakStatus.OffPeak => "🟢",
                    PeakStatus.Peak => "🔴",
                    _ => "🟡"
                },
                statusTitle = state.StatusTitle,
                statusColor = state.StatusColor,
                statusDescription = state.StatusDescription,
                nextChangeLabel = state.NextChangeLabel,
                countdown = state.CountdownText,
                peakHoursLocal = state.PeakHoursLocal,
                workdaysLabel = isPolish ? "Dni robocze" : "Workdays",
                workdaysValue = isPolish ? "Pon–Pt" : "Mon–Fri",
            };

            var dataJson = JsonSerializer.Serialize(data);

            var updateOptions = new WidgetUpdateRequestOptions(widgetId)
            {
                Template = CardTemplate,
                Data = dataJson,
            };

            WidgetManager.GetDefault().UpdateWidget(updateOptions);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Widget update failed: {ex.Message}");
        }
    }
}
