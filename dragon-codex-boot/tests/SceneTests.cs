using System;
using System.IO;
using System.Web.Script.Serialization;
using DragonCodexBoot;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

internal static class SceneTests {
 private static int checks;
 private static void Check(bool ok,string label) { if(!ok)throw new Exception(label);checks++; }
 private static void Reject(Action action,string label) { bool rejected=false;try { action(); }catch(ArgumentException) { rejected=true; }Check(rejected,label); }
 [STAThread] public static int Main(string[] args) {
  try {
   string gateRoot=Path.Combine(Path.GetTempPath(),"duo-ready-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(gateRoot);
   try {
    string selected=Path.Combine(gateRoot,"selected.ready"),stale=Path.Combine(gateRoot,"old.ready");File.WriteAllText(stale,"ready");
    Check(!StartupReadiness.IsReady(selected,true),"Responsive window cannot reveal before the selected wallpaper is ready");
    File.WriteAllText(selected,"pending");Check(!StartupReadiness.IsReady(selected,true),"Incomplete readiness signal cannot reveal the client");
    File.WriteAllText(selected,"ready");Check(StartupReadiness.IsReady(selected,true),"Selected wallpaper signal permits handoff");
    Check(!StartupReadiness.IsReady(selected,false),"Wallpaper readiness never bypasses window readiness");
   }finally{Directory.Delete(gateRoot,true);}
   var timeline=new SceneTimeline(8,4.8);
   timeline.Advance(5,false,false);Check(timeline.Time==4.8&&timeline.Holding,"Slow app clamps exactly at checkpoint");
   timeline.Advance(20,false,false);Check(timeline.Time==4.8,"Waiting discards elapsed wall time");
   timeline.Advance(.2,true,false);Check(Math.Abs(timeline.Time-5)<1e-8&&!timeline.Holding,"Ready app resumes without jump");
   timeline.Advance(10,true,false);Check(timeline.Time==8&&timeline.Finished,"Finish clamps at duration");
   timeline=new SceneTimeline(8,4.8);timeline.Advance(5,true,false);timeline.Advance(3,false,false);
   Check(timeline.Time==5&&timeline.Holding&&!timeline.Finished,"Window lost before transition freezes current scene frame");
   timeline.Advance(.2,true,false);Check(Math.Abs(timeline.Time-5.2)<1e-8&&!timeline.Holding,"Recovered window resumes before transition without jump");
   timeline=new SceneTimeline(8,4.8);timeline.Advance(6.5,true,false);timeline.Advance(10,false,false);
   Check(timeline.Time==6.5&&timeline.Holding&&!timeline.Finished,"Window lost during transition cannot finish the scene");
   timeline.Advance(.2,true,false);Check(Math.Abs(timeline.Time-6.7)<1e-8&&!timeline.Holding,"Recovered window resumes transition without jump");
   timeline=new SceneTimeline(8,4.8);timeline.Advance(9,false,true);Check(timeline.Finished,"Offline preview bypasses readiness hold");
   Reject(()=>timeline.Advance(Double.NaN,true,true),"Reject NaN delta");
   Reject(()=>timeline.Advance(-1,true,true),"Reject negative delta");
   Reject(()=>new SceneTimeline(4,4.8),"Reject checkpoint outside duration");
   var serializer=new JavaScriptSerializer();
   Config c=serializer.Deserialize<Config>(File.ReadAllText(args[0]));Entry.ValidateConfig(c);
   Check(c.Video==null&&c.PlaybackMode=="Scene","Scene works without MP4");
   Config defaults=serializer.Deserialize<Config>("{\"PlaybackMode\":\"Scene\"}");Check(!defaults.AutoReplaceEntrypoints&&!defaults.ScanAllLocalDrives,"Scene missing integration flags defaults to opt out");
   double duration=c.Scene.DurationSeconds;c.Scene.DurationSeconds=Double.NaN;Reject(()=>Entry.ValidateConfig(c),"Reject NaN scene duration");c.Scene.DurationSeconds=duration;
   c.Scene.DurationSeconds=7;Reject(()=>Entry.ValidateConfig(c),"Reject transition beyond scene end");c.Scene.DurationSeconds=8;
   c.PlaybackMode="Other";Reject(()=>Entry.ValidateConfig(c),"Reject unknown mode");c.PlaybackMode="Scene";
   c.Scene.LeftCharacter=" ";Reject(()=>Entry.ValidateConfig(c),"Reject blank asset");
   c.Scene.LeftCharacter="missing.png";Reject(()=>Entry.ValidateAssets(c,Path.GetTempPath()),"Missing assets fail before UI");
   c=serializer.Deserialize<Config>(File.ReadAllText(args[0]));
   c.AppLaunch=null;c.AppExecutable=System.Diagnostics.Process.GetCurrentProcess().MainModule.FileName;
   Entry.ValidateConfig(c);Check(true,"Existing absolute executable supports portable installs");
   c.AppExecutable="relative.exe";Reject(()=>Entry.ValidateConfig(c),"Reject relative executable");
   c.AppExecutable="C:\\missing.exe";Reject(()=>Entry.ValidateConfig(c),"Reject missing executable");
   c.AppExecutable=System.Diagnostics.Process.GetCurrentProcess().MainModule.FileName+" --arg";Reject(()=>Entry.ValidateConfig(c),"Reject executable arguments");
   RenderRegression(serializer.Deserialize<Config>(File.ReadAllText(args[0])));
   Console.WriteLine("PASS: "+checks+" scene/timeline assertions. No client launched.");return 0;
  }catch(Exception e) { Console.Error.WriteLine(e);return 1; }
 }
 private static void RenderRegression(Config c) {
  string root=Path.Combine(Path.GetTempPath(),"duo-scene-tests-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(root);
  try {
   string image=Path.Combine(root,"图 卡.png");
   var visual=new System.Windows.Media.DrawingVisual();using(var dc=visual.RenderOpen()) { dc.DrawRectangle(Brushes.Pink,null,new Rect(0,0,80,80));dc.DrawEllipse(Brushes.Purple,null,new Point(40,30),20,20); }
   var bmp=new RenderTargetBitmap(80,80,96,96,PixelFormats.Pbgra32);bmp.Render(visual);var png=new PngBitmapEncoder();png.Frames.Add(BitmapFrame.Create(bmp));using(var stream=File.Create(image))png.Save(stream);
   c.Scene.Background=c.Scene.LeftCharacter=c.Scene.RightCharacter=image;
   Entry.ValidateAssets(c,root);Check(true,"Unicode image paths decode before rendering");
   string first=Path.Combine(root,"first"),second=Path.Combine(root,"second");SceneView.RenderPreviews(c,root,first);SceneView.RenderPreviews(c,root,second);
   Check(Directory.GetFiles(first,"*.png").Length==4,"Export four snapshots");
   var bytes=File.ReadAllBytes(Path.Combine(first,"scene-1.png"));
   Check(Convert.ToBase64String(bytes)==Convert.ToBase64String(File.ReadAllBytes(Path.Combine(second,"scene-1.png"))),"Same time renders deterministically");
   Check(Convert.ToBase64String(bytes)!=Convert.ToBase64String(File.ReadAllBytes(Path.Combine(first,"scene-3.png"))),"Interaction and handoff produce different visual frames");
   var loaded=SceneView.Load(first,"scene-1.png");Check(loaded.PixelWidth==1280&&loaded.PixelHeight==720,"Preview resolution");
   Reject(()=>SceneView.RenderPreviews(c,root,first),"Never overwrite prior previews");
   c.Scene=new JavaScriptSerializer().Deserialize<SceneConfig>(new JavaScriptSerializer().Serialize(new {
    Background=image,DurationSeconds=8,ShowCharacterLayers=false
   }));
   Entry.ValidateConfig(c);Entry.ValidateAssets(c,root);
   string illustration=Path.Combine(root,"illustration");SceneView.RenderPreviews(c,root,illustration);
   Check(Directory.GetFiles(illustration,"*.png").Length==4,"Illustration-only scene does not require character layers");
   Check(Convert.ToBase64String(bytes)!=Convert.ToBase64String(File.ReadAllBytes(Path.Combine(illustration,"scene-1.png"))),"Illustration mode removes reference cards from rendered output");
   File.WriteAllText(image,"invalid image");Reject(()=>Entry.ValidateAssets(c,root),"Reject undecodable image before UI");
  }finally { Directory.Delete(root,true); }
 }
}
