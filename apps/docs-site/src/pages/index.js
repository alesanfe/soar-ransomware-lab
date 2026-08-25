import React from 'react';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';

export default function Home() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={`${siteConfig.title}`}
      description="Security Orchestration, Automation and Response Laboratory">
      <main style={{padding: '2rem', maxWidth: '800px', margin: '0 auto'}}>
        <h1>{siteConfig.title}</h1>
        <p>{siteConfig.tagline}</p>
        <p>
          This is a laboratory for simulating ransomware incidents and
          orchestrating automated security responses using SOAR playbooks.
        </p>
        <h2>Getting Started</h2>
        <ul>
          <li><Link to="/docs/intro">Getting Started Guide</Link></li>
          <li><Link to="/docs/architecture/overview">Architecture Overview</Link></li>
          <li><Link to="/docs/getting_started/intro">Installation Guide</Link></li>
        </ul>
        <h2>Resources</h2>
        <ul>
          <li><a href="http://localhost:8000/docs">API Swagger UI</a></li>
          <li><a href="http://localhost:8085">Management UI</a></li>
          <li><a href="http://localhost:8084">Grafana</a></li>
          <li><a href="https://github.com/alesanfe/soar-ransomware-lab">GitHub Repository</a></li>
        </ul>
      </main>
    </Layout>
  );
}
