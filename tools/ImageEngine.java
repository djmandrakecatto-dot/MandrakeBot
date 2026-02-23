import com.sun.net.httpserver.HttpServer;
import com.sun.net.httpserver.HttpExchange;
import org.json.JSONObject;
import org.json.JSONArray;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.*;
import java.io.*;
import java.net.InetSocketAddress;
import java.util.Random;

public class ImageEngine {

    public static void main(String[] args) throws Exception {

        HttpServer server = HttpServer.create(new InetSocketAddress(8080), 0);

        server.createContext("/process", exchange -> {

            if (!exchange.getRequestMethod().equalsIgnoreCase("POST")) {
                exchange.sendResponseHeaders(405, -1);
                return;
            }

            try {
                ByteArrayOutputStream baos = new ByteArrayOutputStream();
                exchange.getRequestBody().transferTo(baos);

                DataInputStream dis = new DataInputStream(
                        new ByteArrayInputStream(baos.toByteArray())
                );

                int jsonLength = dis.readInt();
                byte[] jsonBytes = dis.readNBytes(jsonLength);

                JSONObject config = new JSONObject(new String(jsonBytes));
                BufferedImage image = ImageIO.read(dis);

                if (image == null) {
                    exchange.sendResponseHeaders(400, -1);
                    return;
                }

                BufferedImage result = applyEffects(image, config);

                ByteArrayOutputStream out = new ByteArrayOutputStream();
                ImageIO.write(result, "png", out);

                byte[] imageBytes = out.toByteArray();
                exchange.sendResponseHeaders(200, imageBytes.length);
                exchange.getResponseBody().write(imageBytes);

            } catch (Exception e) {
                e.printStackTrace();
                exchange.sendResponseHeaders(500, -1);
            }

            exchange.close();
        });

        server.start();
        System.out.println("Image Engine running on port 8080");
    }

    private static BufferedImage applyEffects(BufferedImage img, JSONObject config) {

        JSONArray effects = config.getJSONArray("effects");

        for (int i = 0; i < effects.length(); i++) {
            JSONObject effect = effects.getJSONObject(i);
            String type = effect.getString("type");

            switch (type) {
                case "invert": img = invert(img); break;
                case "grayscale": img = grayscale(img); break;
                case "sepia": img = sepia(img); break;
                case "solarize": img = solarize(img); break;
                case "posterize": img = posterize(img, effect.optInt("levels", 4)); break;
                case "brightness": img = brightness(img, effect.optInt("amount", 40)); break;
                case "contrast": img = contrast(img, effect.optDouble("amount", 1.5)); break;
                case "blur": img = convolve(img, blurKernel()); break;
                case "sharpen": img = convolve(img, sharpenKernel()); break;
                case "edge": img = convolve(img, edgeKernel()); break;
                case "emboss": img = convolve(img, embossKernel()); break;
                case "neon": img = neon(img); break;
                case "scanlines": img = scanlines(img); break;
                case "vhs": img = vhs(img, effect.optInt("strength", 3)); break;
                case "noise": img = noise(img); break;
                case "pixelate": img = pixelate(img, effect.optInt("size", 10)); break;
                case "stretch": img = stretch(img); break;
                case "swirl": img = swirl(img); break;
                case "heatwave": img = heatwave(img); break;
                case "ghost": img = ghost(img); break;
                case "outline": img = outline(img); break;
                case "glow": img = glow(img); break;
                case "warp": img = warp(img); break;
            }
        }

        return img;
    }
    public static BufferedImage posterize(BufferedImage img, int levels) {
        int width = img.getWidth();
        int height = img.getHeight();

        BufferedImage output = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);

        int step = 256 / levels;

        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {

                int rgba = img.getRGB(x, y);

                int a = (rgba >> 24) & 0xff;
                int r = (rgba >> 16) & 0xff;
                int g = (rgba >> 8) & 0xff;
                int b = rgba & 0xff;

                r = (r / step) * step;
                g = (g / step) * step;
                b = (b / step) * step;

                int newPixel = (a << 24) | (r << 16) | (g << 8) | b;
                output.setRGB(x, y, newPixel);
            }
        }

        return output;
    }
    // ===== BASIC EFFECTS =====

    private static BufferedImage invert(BufferedImage img) {
        BufferedImage out = copy(img);
        for (int y = 0; y < out.getHeight(); y++)
            for (int x = 0; x < out.getWidth(); x++) {
                Color c = new Color(out.getRGB(x,y), true);
                out.setRGB(x,y,new Color(
                        255-c.getRed(),
                        255-c.getGreen(),
                        255-c.getBlue(),
                        c.getAlpha()).getRGB());
            }
        return out;
    }

    private static BufferedImage grayscale(BufferedImage img) {
        BufferedImage out = copy(img);
        for (int y=0;y<out.getHeight();y++)
            for(int x=0;x<out.getWidth();x++){
                Color c=new Color(out.getRGB(x,y),true);
                int avg=(c.getRed()+c.getGreen()+c.getBlue())/3;
                out.setRGB(x,y,new Color(avg,avg,avg,c.getAlpha()).getRGB());
            }
        return out;
    }

    private static BufferedImage sepia(BufferedImage img){
        BufferedImage out=copy(img);
        for(int y=0;y<out.getHeight();y++)
            for(int x=0;x<out.getWidth();x++){
                Color c=new Color(out.getRGB(x,y),true);
                int tr=clamp((int)(0.393*c.getRed()+0.769*c.getGreen()+0.189*c.getBlue()));
                int tg=clamp((int)(0.349*c.getRed()+0.686*c.getGreen()+0.168*c.getBlue()));
                int tb=clamp((int)(0.272*c.getRed()+0.534*c.getGreen()+0.131*c.getBlue()));
                out.setRGB(x,y,new Color(tr,tg,tb,c.getAlpha()).getRGB());
            }
        return out;
    }

    private static BufferedImage solarize(BufferedImage img){
        BufferedImage out=copy(img);
        for(int y=0;y<out.getHeight();y++)
            for(int x=0;x<out.getWidth();x++){
                Color c=new Color(out.getRGB(x,y),true);
                int r=c.getRed()>128?255-c.getRed():c.getRed();
                int g=c.getGreen()>128?255-c.getGreen():c.getGreen();
                int b=c.getBlue()>128?255-c.getBlue():c.getBlue();
                out.setRGB(x,y,new Color(r,g,b,c.getAlpha()).getRGB());
            }
        return out;
    }

    private static BufferedImage brightness(BufferedImage img,int amount){
        BufferedImage out=copy(img);
        for(int y=0;y<out.getHeight();y++)
            for(int x=0;x<out.getWidth();x++){
                Color c=new Color(out.getRGB(x,y),true);
                out.setRGB(x,y,new Color(
                        clamp(c.getRed()+amount),
                        clamp(c.getGreen()+amount),
                        clamp(c.getBlue()+amount),
                        c.getAlpha()).getRGB());
            }
        return out;
    }

    private static BufferedImage contrast(BufferedImage img,double factor){
        BufferedImage out=copy(img);
        for(int y=0;y<out.getHeight();y++)
            for(int x=0;x<out.getWidth();x++){
                Color c=new Color(out.getRGB(x,y),true);
                int r=clamp((int)((c.getRed()-128)*factor+128));
                int g=clamp((int)((c.getGreen()-128)*factor+128));
                int b=clamp((int)((c.getBlue()-128)*factor+128));
                out.setRGB(x,y,new Color(r,g,b,c.getAlpha()).getRGB());
            }
        return out;
    }

    private static BufferedImage noise(BufferedImage img){
        BufferedImage out=copy(img);
        Random rand=new Random();
        for(int y=0;y<out.getHeight();y++)
            for(int x=0;x<out.getWidth();x++){
                Color c=new Color(out.getRGB(x,y),true);
                int n=rand.nextInt(50)-25;
                out.setRGB(x,y,new Color(
                        clamp(c.getRed()+n),
                        clamp(c.getGreen()+n),
                        clamp(c.getBlue()+n),
                        c.getAlpha()).getRGB());
            }
        return out;
    }

    // ===== CONVOLUTION =====

    private static BufferedImage convolve(BufferedImage img, float[] kernel){
        Kernel k=new Kernel(3,3,kernel);
        ConvolveOp op=new ConvolveOp(k,ConvolveOp.EDGE_NO_OP,null);
        return op.filter(img,null);
    }

    private static float[] blurKernel(){
        return new float[]{
                1/9f,1/9f,1/9f,
                1/9f,1/9f,1/9f,
                1/9f,1/9f,1/9f};
    }

    private static float[] sharpenKernel(){
        return new float[]{
                0,-1,0,
                -1,5,-1,
                0,-1,0};
    }

    private static float[] edgeKernel(){
        return new float[]{
                -1,-1,-1,
                -1,8,-1,
                -1,-1,-1};
    }

    private static float[] embossKernel(){
        return new float[]{
                -2,-1,0,
                -1,1,1,
                0,1,2};
    }

    // ===== SPECIAL =====

    private static BufferedImage neon(BufferedImage img){
        return convolve(grayscale(img), edgeKernel());
    }

    private static BufferedImage scanlines(BufferedImage img){
        BufferedImage out=copy(img);
        for(int y=0;y<out.getHeight();y+=2)
            for(int x=0;x<out.getWidth();x++){
                Color c=new Color(out.getRGB(x,y),true);
                out.setRGB(x,y,new Color(
                        c.getRed()/2,
                        c.getGreen()/2,
                        c.getBlue()/2,
                        c.getAlpha()).getRGB());
            }
        return out;
    }

    private static BufferedImage vhs(BufferedImage img,int strength){
        BufferedImage out=new BufferedImage(
                img.getWidth(),img.getHeight(),BufferedImage.TYPE_INT_ARGB);
        for(int y=0;y<img.getHeight();y++){
            int shift=(int)(Math.sin(y*0.1)*strength);
            for(int x=0;x<img.getWidth();x++){
                int nx=(x+shift)%img.getWidth();
                if(nx<0) nx+=img.getWidth();
                out.setRGB(nx,y,img.getRGB(x,y));
            }
        }
        return out;
    }

    private static BufferedImage pixelate(BufferedImage img,int size){
        BufferedImage out=copy(img);
        for(int y=0;y<out.getHeight();y+=size)
            for(int x=0;x<out.getWidth();x+=size){
                int rgb=out.getRGB(x,y);
                for(int dy=0;dy<size && y+dy<out.getHeight();dy++)
                    for(int dx=0;dx<size && x+dx<out.getWidth();dx++)
                        out.setRGB(x+dx,y+dy,rgb);
            }
        return out;
    }

    private static BufferedImage stretch(BufferedImage img){
        Image tmp=img.getScaledInstance(img.getWidth()*2,img.getHeight(),Image.SCALE_SMOOTH);
        BufferedImage out=new BufferedImage(
                img.getWidth(),img.getHeight(),BufferedImage.TYPE_INT_ARGB);
        Graphics2D g=out.createGraphics();
        g.drawImage(tmp,0,0,img.getWidth(),img.getHeight(),null);
        g.dispose();
        return out;
    }

    private static BufferedImage swirl(BufferedImage img){
        BufferedImage out=new BufferedImage(
                img.getWidth(),img.getHeight(),BufferedImage.TYPE_INT_ARGB);
        int cx=img.getWidth()/2;
        int cy=img.getHeight()/2;
        for(int y=0;y<img.getHeight();y++)
            for(int x=0;x<img.getWidth();x++){
                int dx=x-cx;
                int dy=y-cy;
                double dist=Math.sqrt(dx*dx+dy*dy);
                double angle=Math.atan2(dy,dx)+dist*0.0005;
                int nx=(int)(cx+dist*Math.cos(angle));
                int ny=(int)(cy+dist*Math.sin(angle));
                if(nx>=0 && ny>=0 && nx<img.getWidth() && ny<img.getHeight())
                    out.setRGB(x,y,img.getRGB(nx,ny));
            }
        return out;
    }

    private static BufferedImage heatwave(BufferedImage img){
        return vhs(img,8);
    }

    private static BufferedImage ghost(BufferedImage img){
        BufferedImage out=copy(img);
        Graphics2D g=out.createGraphics();
        g.setComposite(AlphaComposite.getInstance(AlphaComposite.SRC_OVER,0.5f));
        g.drawImage(img,10,10,null);
        g.dispose();
        return out;
    }

    private static BufferedImage outline(BufferedImage img){
        return convolve(img,edgeKernel());
    }

    private static BufferedImage glow(BufferedImage img){
        BufferedImage out=copy(img);
        Graphics2D g=out.createGraphics();
        g.setComposite(AlphaComposite.getInstance(AlphaComposite.SRC_OVER,0.3f));
        g.setColor(Color.WHITE);
        g.fillRect(0,0,out.getWidth(),out.getHeight());
        g.dispose();
        return out;
    }

    private static BufferedImage warp(BufferedImage img){
        return vhs(img,10);
    }

    // ===== UTIL =====

    private static int clamp(int v){
        return Math.max(0,Math.min(255,v));
    }

    private static BufferedImage copy(BufferedImage img){
        BufferedImage copy=new BufferedImage(
                img.getWidth(),img.getHeight(),
                BufferedImage.TYPE_INT_ARGB);
        Graphics2D g=copy.createGraphics();
        g.drawImage(img,0,0,null);
        g.dispose();
        return copy;
    }
}