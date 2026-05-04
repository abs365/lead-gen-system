import "./globals.css";
import AuthProvider from "@/components/AuthProvider";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, padding: 0, background: "#0f172a", color: "#f1f5f9", fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif", minHeight: "100vh" }}>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}