'use client';

import 'lightgallery/css/lightgallery.css';
import 'lightgallery/css/lg-zoom.css';
import 'lightgallery/css/lg-thumbnail.css';
import 'lightgallery/css/lg-autoplay.css';
import 'lightgallery/css/lg-fullscreen.css';
import 'lightgallery/css/lg-share.css';
import 'lightgallery/css/lg-zoom.css';

import '../../../public/assets/icons/iconly/index.min.css';
import '../../../public/assets/vendor/swiper/swiper-bundle.min.css';
import '../../../public/assets/vendor/animate/animate.css';
import '../../../public/assets/css/style.css';
import '../../../public/assets/css/skin/skin-1.css';
import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
// import SubscribeModal from "@/constant/SubscribeModal";
import ScrollToTopButton from '@/constant/ScrollToTopButton';
import { AuthProvider } from '@/context/AuthContext';
import { CartProvider } from '@/context/CartContext';

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const path = usePathname();

  useEffect(() => {
    setTimeout(() => {
      const links = document.querySelectorAll('a[href="#"]');
      const handleClick = (event: any) => {
        event.preventDefault();
      };
      if (links) {
        links.forEach(link => {
          link.addEventListener('click', handleClick);
        });
      }
    }, 600);
  }, [path]);

  useEffect(() => {
    setTimeout(() => {
      const { WOW } = require('wowjs');
      const wow = new WOW({
        boxClass: 'wow',
        animateClass: 'animated',
        offset: 0,
        mobile: false,
        once: true,
        live: false,
        callback: function (box: HTMLElement) {
          box.classList.add('will-animate');
          box.classList.add('animated');
        },
      });
      wow.init();
    }, 100);
  }, [path]);
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Roboto:wght@100;300;400;500;700;900&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <AuthProvider>
          <CartProvider>{children}</CartProvider>
        </AuthProvider>
        <ScrollToTopButton />
      </body>
    </html>
  );
}
