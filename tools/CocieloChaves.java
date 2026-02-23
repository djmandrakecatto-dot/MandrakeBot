import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

public class CocieloChaves {
    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: java CocieloChaves <payload.json>");
            System.exit(1);
        }

        Path payloadPath = Path.of(args[0]);

        try {
            byte[] body = Files.readAllBytes(payloadPath);

            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(20))
                    .build();

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create("https://gabriela.loritta.website/api/v1/videos/cocielo-chaves"))
                    .timeout(Duration.ofSeconds(180))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofByteArray(body))
                    .build();

            HttpResponse<byte[]> response = client.send(request, HttpResponse.BodyHandlers.ofByteArray());

            int status = response.statusCode();
            if (status >= 400 && status < 500) {
                System.err.println("Client error: " + status);
                try { System.err.println(new String(response.body())); } catch (Exception ignored) {}
                System.exit(2);
            } else if (status < 200 || status >= 300) {
                System.err.println("Server error: " + status);
                try { System.err.println(new String(response.body())); } catch (Exception ignored) {}
                System.exit(3);
            }

            System.out.write(response.body());
            System.out.flush();

        } catch (IOException e) {
            System.err.println("I/O error: " + e.getMessage());
            System.exit(4);
        } catch (InterruptedException e) {
            System.err.println("Interrupted: " + e.getMessage());
            Thread.currentThread().interrupt();
            System.exit(5);
        } catch (Exception e) {
            System.err.println("Unexpected error: " + e);
            System.exit(6);
        }
    }
}
