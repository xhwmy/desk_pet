$ErrorActionPreference='Stop'
if (!("BambooDuo.WindowFrame" -as [type])) {
 Add-Type -TypeDefinition @"
using System;using System.Collections.Generic;using System.Runtime.InteropServices;
namespace BambooDuo { public static class WindowFrame {
 public delegate bool Callback(IntPtr h,IntPtr p);
 [StructLayout(LayoutKind.Sequential)] public struct Rect {public int Left,Top,Right,Bottom;}
 [DllImport("user32.dll")] static extern bool EnumWindows(Callback cb,IntPtr p);
 [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h,out uint id);
 [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] static extern int GetWindowLong(IntPtr h,int index);
 [DllImport("user32.dll")] static extern int SetWindowLong(IntPtr h,int index,int value);
 [DllImport("user32.dll")] static extern bool SetWindowPos(IntPtr h,IntPtr after,int x,int y,int w,int ht,uint flags);
 [DllImport("dwmapi.dll")] static extern int DwmSetWindowAttribute(IntPtr h,int key,ref int val,int size);
 [DllImport("dwmapi.dll")] static extern int DwmGetWindowAttribute(IntPtr h,int key,out Rect val,int size);
 public static string[] Restore(int[] processIds) {
  var ids=new HashSet<int>(processIds);var result=new List<string>();
  EnumWindows((h,p)=>{uint id;GetWindowThreadProcessId(h,out id);int style=GetWindowLong(h,-16);
   if(ids.Contains((int)id)&&IsWindowVisible(h)&&(style&0x00C00000)==0x00C00000) {
    int updated=style|0x00080000|0x00030000;SetWindowLong(h,-16,updated);
    int dark=1,caption=0x00212D2C,text=0x00EDF1F4;
    DwmSetWindowAttribute(h,20,ref dark,4);DwmSetWindowAttribute(h,35,ref caption,4);DwmSetWindowAttribute(h,36,ref text,4);
    SetWindowPos(h,IntPtr.Zero,0,0,0,0,0x37);
    Rect bounds;int hr=DwmGetWindowAttribute(h,5,out bounds,16);
    result.Add("window="+h+" systemMenu="+((GetWindowLong(h,-16)&0x80000)!=0)+" captionBoundsResult="+hr+" bounds="+bounds.Left+","+bounds.Top+","+bounds.Right+","+bounds.Bottom);
   }return true;},IntPtr.Zero);return result.ToArray();
 }
}}
"@
}
$store=Get-AppxPackage -Name OpenAI.Codex | Select-Object -First 1
$app=Join-Path $store.InstallLocation 'app/ChatGPT.exe'
$ids=@(Get-CimInstance Win32_Process -Filter "Name='ChatGPT.exe'" | Where-Object {$_.ExecutablePath -eq $app -and $_.CommandLine -notmatch '--type='} | ForEach-Object {[int]$_.ProcessId})
$restored=[BambooDuo.WindowFrame]::Restore([int[]]$ids)
if(!$restored.Count) { throw 'The main Codex window frame is not ready.' }
$restored
