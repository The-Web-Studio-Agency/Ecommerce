import PluginInit from "@/helper/PluginInit";
import "./font.css";
import "./globals.css";
import "react-quill-new/dist/quill.snow.css";
import "jsvectormap/dist/jsvectormap.css";
import "react-toastify/dist/ReactToastify.css";
import "react-modal-video/css/modal-video.min.css";

export const metadata = {
  title: "WowDash NEXT JS - Admin Dashboard Multipurpose Bootstrap 5 Template",
  description:
    "Wowdash NEXT JS is a developer-friendly, ready-to-use admin template designed for building attractive, scalable, and high-performing web applications.",
};

export default function RootLayout({ children }) {
  return (
    <html lang='en'>
      <head>
        <link rel="stylesheet" href="/assets/admin-css/remixicon.css" />
        <link rel="stylesheet" href="/assets/admin-css/lib/bootstrap.min.css" />
        <link rel="stylesheet" href="/assets/admin-css/lib/apexcharts.css" />
        <link rel="stylesheet" href="/assets/admin-css/lib/dataTables.min.css" />
        <link rel="stylesheet" href="/assets/admin-css/lib/editor-katex.min.css" />
        <link rel="stylesheet" href="/assets/admin-css/lib/editor.atom-one-dark.min.css" />
        <link rel="stylesheet" href="/assets/admin-css/lib/editor.quill.snow.css" />
        <link rel="stylesheet" href="/assets/admin-css/lib/flatpickr.min.css" />
        <link rel="stylesheet" href="/assets/admin-css/lib/full-calendar.css" />
        <link rel="stylesheet" href="/assets/admin-css/lib/jquery-jvectormap-2.0.5.css" />
        <link rel="stylesheet" href="/assets/admin-css/lib/magnific-popup.css" />
        <link rel="stylesheet" href="/assets/admin-css/lib/slick.css" />
        <link rel="stylesheet" href="/assets/admin-css/lib/prism.css" />
        <link rel="stylesheet" href="/assets/admin-css/lib/file-upload.css" />
        <link rel="stylesheet" href="/assets/admin-css/lib/audioplayer.css" />
        <link rel="stylesheet" href="/assets/admin-css/lib/animate.min.css" />
        <link rel="stylesheet" href="/assets/admin-css/style.css" />
        <link rel="stylesheet" href="/assets/admin-css/extra.css" />
      </head>
      <PluginInit />
      <body suppressHydrationWarning={true}>{children}</body>
    </html>
  );
}
