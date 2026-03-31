using System.Runtime.InteropServices;
using Microsoft.Windows.Widgets;
using Microsoft.Windows.Widgets.Providers;
using WinRT;

namespace ClaudePeakWidget;

// COM class factory — creates WidgetProvider instances when Windows requests them.
[ComVisible(true)]
[ClassInterface(ClassInterfaceType.None)]
[Guid(Program.WidgetProviderClsid)]
public class WidgetProviderFactory : IClassFactory
{
    public int CreateInstance(IntPtr pUnkOuter, ref Guid riid, out IntPtr ppvObject)
    {
        ppvObject = IntPtr.Zero;
        if (pUnkOuter != IntPtr.Zero)
            return unchecked((int)0x80040110); // CLASS_E_NOAGGREGATION

        var provider = new WidgetProvider();
        ppvObject = MarshalInterface<IWidgetProvider>.FromManaged(provider);
        return 0; // S_OK
    }

    public int LockServer(bool fLock) => 0; // S_OK
}

[ComImport]
[Guid("00000001-0000-0000-C000-000000000046")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IClassFactory
{
    [PreserveSig]
    int CreateInstance(IntPtr pUnkOuter, ref Guid riid, out IntPtr ppvObject);
    [PreserveSig]
    int LockServer(bool fLock);
}

public static class Program
{
    // Unique CLSID for our widget provider — must match Package.appxmanifest
    public const string WidgetProviderClsid = "E5B3F02A-7B7E-4A5D-9C1F-8D2E6A3B4C5D";

    private const uint CLSCTX_LOCAL_SERVER = 0x4;
    private const uint REGCLS_MULTIPLEUSE = 1;

    [DllImport("ole32.dll")]
    private static extern int CoRegisterClassObject(
        ref Guid rclsid,
        [MarshalAs(UnmanagedType.IUnknown)] object pUnk,
        uint dwClsContext,
        uint flags,
        out uint lpdwRegister);

    [STAThread]
    static void Main(string[] args)
    {
        // Required for WinRT COM interop
        ComWrappersSupport.InitializeComWrappers();

        // Register our COM class factory so the Widget Host can activate us
        var clsid = Guid.Parse(WidgetProviderClsid);
        var factory = new WidgetProviderFactory();

        int hr = CoRegisterClassObject(
            ref clsid,
            factory,
            CLSCTX_LOCAL_SERVER,
            REGCLS_MULTIPLEUSE,
            out uint cookie);

        if (hr != 0)
        {
            Console.Error.WriteLine($"CoRegisterClassObject failed: 0x{hr:X8}");
            return;
        }

        Console.WriteLine("Claude Peak Hours Widget Provider running...");
        Console.WriteLine("Press Ctrl+C to stop.");

        // Keep the process alive — Widget Host sends COM calls here
        var exitEvent = new ManualResetEvent(false);
        Console.CancelKeyPress += (_, e) =>
        {
            e.Cancel = true;
            exitEvent.Set();
        };
        exitEvent.WaitOne();
    }
}
