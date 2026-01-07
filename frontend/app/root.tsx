import { Links, Meta, Outlet, Scripts, ScrollRestoration } from "react-router";
import { AppProvider } from "@shopify/polaris";
import enTranslations from "@shopify/polaris/locales/en.json";
import "@shopify/polaris/build/esm/styles.css";
import "./styles/global.css";

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <Meta />
        <Links />
      </head>
      <body>
        {children}
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}

export default function App() {
  return (
    <AppProvider i18n={enTranslations}>
      <Outlet />
    </AppProvider>
  );
}

export function ErrorBoundary({ error }: { error: Error }) {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Error - EcomDash V2</title>
      </head>
      <body>
        <div style={{ padding: "2rem", fontFamily: "system-ui" }}>
          <h1>Something went wrong</h1>
          <p>{error.message}</p>
        </div>
      </body>
    </html>
  );
}
