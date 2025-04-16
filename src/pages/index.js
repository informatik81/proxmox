import React from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import HomepageFeatures from '@site/src/components/HomepageFeatures';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <h1 className="hero__title">{siteConfig.title}</h1>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/intro">
            Commencer l'apprentissage 📚
          </Link>
          <Link
            className="button button--secondary button--lg"
            to="/docs/depannage">
            Guide de dépannage
          </Link>
          <Link
            className="button button--secondary button--lg"
            to="/docs/tutorials">
            Tutoriels vidéo
          </Link>
          <Link
            className="button button--secondary button--lg"
            to="/docs/testimonials">
            Témoignages
          </Link>
          <Link
            className="button button--secondary button--lg"
            to="/blog">
            Blog
          </Link>
        </div>
      </div>
    </header>
  );
}

export default function Home() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={`Accueil`}
      description="Base de connaissances avancée sur Proxmox VE et Proxmox Backup Server">
      <HomepageHeader />
      <main>
        <HomepageFeatures />
      </main>
    </Layout>
  );
}