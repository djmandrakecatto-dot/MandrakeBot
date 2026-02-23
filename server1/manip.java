import com.sun.net.httpserver.HttpServer;
import com.sun.net.httpserver.HttpExchange;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.geom.AffineTransform;
import java.awt.image.BufferedImage;
import java.io.*;
import java.net.InetSocketAddress;

public class manip {

    public static void main(String[] args) throws Exception {
        HttpServer server = HttpServer.create(
    new InetSocketAddress("26.199.50.19", 8081),
    0
);

        server.createContext("/process", manip::handleProcess);
        server.setExecutor(null); // default thread pool
        System.out.println("Java Image Server running on :8081");
        server.start();
    }

    private static void handleProcess(HttpExchange ex) throws IOException {
        if (!ex.getRequestMethod().equalsIgnoreCase("POST")) {
            ex.sendResponseHeaders(405, -1);
            return;
        }

        String manip = ex.getRequestHeaders().getFirst("X-Manip-Type");
        String angleHeader = ex.getRequestHeaders().getFirst("X-Angle");
        double angle = angleHeader != null ? Math.toRadians(Double.parseDouble(angleHeader)) : 0;

        BufferedImage input = ImageIO.read(ex.getRequestBody());
        if (input == null) {
            ex.sendResponseHeaders(400, -1);
            return;
        }

        BufferedImage output;

        switch (manip) {
            case "spin_cube":
                output = spinCubeEffect(input, angle);
                break;
            case "rotate":
                output = rotateImage(input, angle);
                break;
            case "grayscale":
                output = grayscale(input);
                break;
            default:
                ex.sendResponseHeaders(400, -1);
                return;
        }

        ex.getResponseHeaders().add("Content-Type", "image/png");
        ex.sendResponseHeaders(200, 0);

        OutputStream os = ex.getResponseBody();
        ImageIO.write(output, "png", os);
        os.close();
    }

    // -------------------------
    // IMAGE OPS
    // -------------------------

    private static BufferedImage grayscale(BufferedImage img) {
        BufferedImage out = new BufferedImage(
                img.getWidth(), img.getHeight(), BufferedImage.TYPE_INT_ARGB
        );

        for (int y = 0; y < img.getHeight(); y++) {
            for (int x = 0; x < img.getWidth(); x++) {
                int rgb = img.getRGB(x, y);
                Color c = new Color(rgb, true);
                int g = (c.getRed() + c.getGreen() + c.getBlue()) / 3;
                out.setRGB(x, y, new Color(g, g, g, c.getAlpha()).getRGB());
            }
        }
        return out;
    }

    private static BufferedImage rotateImage(BufferedImage img, double angle) {
        int w = img.getWidth();
        int h = img.getHeight();

        BufferedImage out = new BufferedImage(w, h, BufferedImage.TYPE_INT_ARGB);
        Graphics2D g = out.createGraphics();

        g.setRenderingHint(RenderingHints.KEY_INTERPOLATION,
                RenderingHints.VALUE_INTERPOLATION_BILINEAR);

        AffineTransform at = new AffineTransform();
        at.translate(w / 2.0, h / 2.0);
        at.rotate(angle);
        at.translate(-w / 2.0, -h / 2.0);

        g.drawImage(img, at, null);
        g.dispose();
        return out;
    }

    // -------------------------
    // "3D" SPIN CUBE EFFECT
    // -------------------------

    private static BufferedImage spinCubeEffect(BufferedImage img, double angle) {
        int w = img.getWidth();
        int h = img.getHeight();

        BufferedImage out = new BufferedImage(w, h, BufferedImage.TYPE_INT_ARGB);

        double cx = w / 2.0;
        double cy = h / 2.0;
        double depth = 400;

        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {

                double dx = x - cx;
                double dy = y - cy;

                // fake 3D rotation (Y axis)
                double dz = Math.sin(angle) * dx;
                double px = Math.cos(angle) * dx;

                double scale = depth / (depth + dz);

                int sx = (int) (cx + px * scale);
                int sy = (int) (cy + dy * scale);

                if (sx >= 0 && sy >= 0 && sx < w && sy < h) {
                    out.setRGB(x, y, img.getRGB(sx, sy));
                }
            }
        }
        return out;
    }
}
