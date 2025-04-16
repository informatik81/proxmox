import React from 'react';
import clsx from 'clsx';
import styles from './styles.module.css';

const FeatureList = [
  {
    title: 'Proxmox VE',
    Svg: require('@site/static/img/proxmox-ve-icon.svg').default,
    description: (
      <>
        Découvrez comment installer, configurer et administrer Proxmox Virtual Environment,
        la plateforme de virtualisation open-source basée sur KVM et LXC.
      </>
    ),
  },
  {
    title: 'Proxmox Backup Server',
    Svg: require('@site/static/img/proxmox-pbs-icon.svg').default,
    description: (
      <>
        Apprenez à mettre en place une solution de sauvegarde robuste avec Proxmox Backup Server,
        pour protéger vos machines virtuelles et conteneurs.
      </>
    ),
  },
  {
    title: 'Tutoriels Pratiques',
    Svg: require('@site/static/img/tutorial-icon.svg').default,
    description: (
      <>
        Consultez nos guides pas à pas et tutoriels vidéo pour maîtriser les fonctionnalités
        avancées de l'écosystème Proxmox.
      </>
    ),
  },
];

function Feature({Svg, title, description}) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center">
        <Svg className={styles.featureSvg} role="img" />
      </div>
      <div className="text--center padding-horiz--md">
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}