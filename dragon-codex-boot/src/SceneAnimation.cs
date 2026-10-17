using System;
using System.IO;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace DragonCodexBoot {
 public sealed class SceneConfig {
  public SceneConfig() { ShowCharacterLayers=true; }
  public bool ShowCharacterLayers { get; set; }
  public string Background { get; set; }
  public string LeftCharacter { get; set; }
  public string RightCharacter { get; set; }
  public double DurationSeconds { get; set; }
 }
 public sealed class SceneTimeline {
  private readonly double duration,holdAt;
  public double Time { get; private set; }
  public bool Holding { get; private set; }
  public bool Finished { get { return Time>=duration; } }
  public SceneTimeline(double durationSeconds,double holdSeconds) {
   if(!Finite(durationSeconds)||!Finite(holdSeconds)||holdSeconds<=0||durationSeconds<=holdSeconds)
    throw new ArgumentException("Scene duration must exceed the positive hold checkpoint.");
   duration=durationSeconds;holdAt=holdSeconds;
  }
  private static bool Finite(double n) { return !Double.IsNaN(n)&&!Double.IsInfinity(n); }
  public void Advance(double delta,bool ready,bool preview) {
   if(!Finite(delta)||delta<0)throw new ArgumentException("Scene delta must be finite and nonnegative.");
   double next=Math.Min(duration,Time+delta);
   Holding=!preview&&!ready&&next>=holdAt&&!Finished;
   // Once past the checkpoint, losing the window freezes this frame rather than
   // rewinding to the checkpoint or spending elapsed wait time on recovery.
   Time=Holding?Math.Max(Time,holdAt):next;
  }
 }
 // The complete visual is deterministic at any timestamp, including offline PNG export.
 public sealed class SceneView:FrameworkElement {
  private readonly BitmapImage background,left,right;
  private readonly Config cfg;
  private readonly bool referenceCards;
  private double time;
  public SceneView(Config c,string root) {
   cfg=c;background=Load(root,c.Scene.Background);
   if(c.Scene.ShowCharacterLayers) {
    left=Load(root,c.Scene.LeftCharacter);right=Load(root,c.Scene.RightCharacter);
    referenceCards=Path.GetExtension(c.Scene.LeftCharacter).Equals(".jpg",StringComparison.OrdinalIgnoreCase)
     ||Path.GetExtension(c.Scene.RightCharacter).Equals(".jpg",StringComparison.OrdinalIgnoreCase);
   }
   ClipToBounds=true;
  }
  public void SetTime(double seconds) {
   if(Double.IsNaN(seconds)||Double.IsInfinity(seconds)||seconds<0)throw new ArgumentException("Invalid scene timestamp.");
   time=seconds;InvalidateVisual();
  }
  public static BitmapImage Load(string root,string path) {
   using(var stream=new FileStream(Path.GetFullPath(Path.Combine(root,path)),FileMode.Open,FileAccess.Read,FileShare.Read)) {
    var image=new BitmapImage();image.BeginInit();image.CacheOption=BitmapCacheOption.OnLoad;
    image.StreamSource=stream;image.EndInit();image.Freeze();return image;
   }
  }
  private static void Image(DrawingContext dc,BitmapSource image,Rect rect,bool fill) {
   double scale=fill?Math.Max(rect.Width/image.PixelWidth,rect.Height/image.PixelHeight):Math.Min(rect.Width/image.PixelWidth,rect.Height/image.PixelHeight);
   double w=image.PixelWidth*scale,h=image.PixelHeight*scale;
   dc.PushClip(new RectangleGeometry(rect));dc.DrawImage(image,new Rect(rect.X+(rect.Width-w)/2,rect.Y+(rect.Height-h)/2,w,h));dc.Pop();
  }
  private static void Text(DrawingContext dc,string value,double size,Brush brush,double x,double y) {
   var text=new FormattedText(value,System.Globalization.CultureInfo.GetCultureInfo("zh-CN"),FlowDirection.LeftToRight,new Typeface("Microsoft YaHei UI"),size,brush,1);
   dc.DrawText(text,new Point(x,y));
  }
  private void Character(DrawingContext dc,BitmapSource image,bool isLeft) {
   double enter=Geometry.Ease(time/1.5),approach=Geometry.Ease((time-1.6)/1.8);
   double x=isLeft?-480+enter*690+approach*95:1920-enter*710-approach*95;
   double bob=Math.Sin(Math.Max(0,time-1.5)*2.5+(isLeft?0:Math.PI))*(time>1.5?9:0);
   Rect box=new Rect(x,228+bob,500,690);
   dc.PushOpacity(enter);dc.PushTransform(new RotateTransform(Math.Sin(time*1.6+(isLeft?0:Math.PI))*1.2,box.X+250,box.Bottom));
   if(referenceCards)dc.DrawRoundedRectangle(new SolidColorBrush(Color.FromArgb(195,255,255,255)),null,new Rect(box.X-8,box.Y-8,box.Width+16,box.Height+16),28,28);
   Image(dc,image,box,false);dc.Pop();dc.Pop();
  }
  protected override void OnRender(DrawingContext dc) {
   base.OnRender(dc);double scale=Math.Min(ActualWidth/1920,ActualHeight/1080);
   dc.DrawRectangle(Brushes.Black,null,new Rect(0,0,ActualWidth,ActualHeight));if(scale<=0)return;
   dc.PushTransform(new TranslateTransform((ActualWidth-1920*scale)/2,(ActualHeight-1080*scale)/2));dc.PushTransform(new ScaleTransform(scale,scale));
   dc.PushClip(new RectangleGeometry(new Rect(0,0,1920,1080)));
   Image(dc,background,new Rect(0,0,1920,1080),true);
   dc.DrawRectangle(new SolidColorBrush(Color.FromArgb((byte)(cfg.Scene.ShowCharacterLayers?108:18),20,46,49)),null,new Rect(0,0,1920,1080));
   if(cfg.Scene.ShowCharacterLayers) { Character(dc,left,true);Character(dc,right,false); }
   for(int i=0;i<40;i++) {
    double x=(i*151.7+time*(12+i%7))%1920,y=(i*97.1-time*(18+i%11))%1080;if(y<0)y+=1080;
    double opacity=.25+.5*(.5+.5*Math.Sin(time*1.8+i));
    dc.DrawEllipse(new SolidColorBrush(Color.FromArgb((byte)(opacity*180),255,230,206)),null,new Point(x,y),2+i%3,2+i%3);
   }
   double interaction=cfg.Scene.ShowCharacterLayers?Geometry.Ease((time-2.2)/.7)*(1-Geometry.Ease((time-5.3)/.6)):0;
   dc.PushOpacity(interaction);double pulse=1+.06*Math.Sin(time*4);
   dc.DrawEllipse(new SolidColorBrush(Color.FromArgb(90,255,222,233)),new Pen(new SolidColorBrush(Color.FromArgb(180,255,238,218)),3),new Point(960,530),78*pulse,78*pulse);
   Text(dc,"✦",70,Brushes.White,924,477);Text(dc,"一起开启新的灵感",24,Brushes.White,850,642);dc.Pop();
   if(time>=cfg.TransitionStart) {
    double a=Geometry.Ease((time-cfg.TransitionStart)/(cfg.TransitionEnd-cfg.TransitionStart));
    Bounds frame=Geometry.Dest(cfg.ScreenFrames,time,1920,1080,a);
    dc.DrawRoundedRectangle(new SolidColorBrush(Color.FromArgb((byte)(a*240),238,246,242)),new Pen(new SolidColorBrush(Color.FromArgb((byte)(a*255),255,244,222)),4),new Rect(frame.Left,frame.Top,frame.Width,frame.Height),12*(1-a),12*(1-a));
    dc.PushOpacity(a);Text(dc,"CODEX",34,new SolidColorBrush(Color.FromRgb(70,102,93)),frame.Left+36,frame.Top+30);dc.Pop();
   }
   if(referenceCards)Text(dc,"参考图占位预览 · 可替换为透明人物 PNG",20,new SolidColorBrush(Color.FromArgb(210,255,255,255)),52,1005);
   dc.Pop();dc.Pop();dc.Pop();
  }
  public static void RenderPreviews(Config cfg,string root,string outputDirectory) {
   string output=Path.GetFullPath(outputDirectory);
   double[] times={0.7,3.2,4.8,6.8};
   string[] paths=new string[times.Length];
   for(int i=0;i<times.Length;i++) {
    paths[i]=Path.Combine(output,"scene-"+i+".png");
    if(File.Exists(paths[i])||Directory.Exists(paths[i]))throw new ArgumentException("Preview output already exists: "+paths[i]);
   }
   SceneView scene=new SceneView(cfg,root);scene.Measure(new Size(1280,720));scene.Arrange(new Rect(0,0,1280,720));
   Directory.CreateDirectory(output);
   for(int i=0;i<times.Length;i++) {
    scene.SetTime(times[i]);scene.UpdateLayout();var bitmap=new RenderTargetBitmap(1280,720,96,96,PixelFormats.Pbgra32);bitmap.Render(scene);
    var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bitmap));
    using(var stream=new FileStream(paths[i],FileMode.CreateNew,FileAccess.Write))encoder.Save(stream);
   }
  }
 }
}
