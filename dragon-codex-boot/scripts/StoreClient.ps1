function Get-StoreClientProcesses {
    # An update can register a new package while the previous version is still running.
    Get-CimInstance Win32_Process -Filter "Name='ChatGPT.exe'" | Where-Object {
        $_.ExecutablePath -match '\\WindowsApps\\OpenAI\.Codex_[^\\]+\\app\\ChatGPT\.exe$'
    }
}

function Start-StoreClient {
    param([string]$Aumid, [int]$Port=9341, [switch]$Normal)
    if (!("BambooDuo.StoreActivation" -as [type])) {
        Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
namespace BambooDuo {
 [ComImport, Guid("2e941141-7f97-4756-ba1d-9decde894a3d"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
 public interface IActivation {
  [PreserveSig] int ActivateApplication([In, MarshalAs(UnmanagedType.LPWStr)] string appId, [In, MarshalAs(UnmanagedType.LPWStr)] string arguments, [In] int options, [Out] out uint pid);
 }
 [ComImport, Guid("45BA127D-10A8-46EA-8AB7-56EA9078943C")] public class ActivationManager {}
 public static class StoreActivation {
  public static uint Launch(string id, string arguments) {
   uint pid; var manager=(IActivation)new ActivationManager();
   int result=manager.ActivateApplication(id,arguments,0,out pid);
   if(result!=0) Marshal.ThrowExceptionForHR(result);
   return pid;
  }
 }
}
"@
    }
    # Store applications require registered activation rather than direct EXE execution.
    $activationArguments=if($Normal) { '' } else { "--remote-debugging-address=127.0.0.1 --remote-debugging-port=$Port" }
    return [BambooDuo.StoreActivation]::Launch($Aumid,$activationArguments)
}
