export default function About() {
  return (
    <main className="page form-page">
      <div className="eyebrow">ABOUT RIVERGUARD</div>
      <h1>One river. Shared responsibility.</h1>
      <p>
        Report what you observe, understand the connected downstream path, and
        track the review.
      </p>
      <section className="card">
        <h2>How it works</h2>
        <ol className="timeline">
          <li>
            <b>Find your place on the river</b>
            <p>
              Tap the mapped river or a nearby point. RiverGuard finds the
              nearest mapped segment and shows the snap distance.
            </p>
          </li>
          <li>
            <b>Share an observation</b>
            <p>
              Add a category, time, description, and optional photo. Every new
              report starts unverified.
            </p>
          </li>
          <li>
            <b>Understand potential impact</b>
            <p>
              The directed network follows downstream connections to mapped
              assets. The score explains every contributing factor.
            </p>
          </li>
          <li>
            <b>Follow the history</b>
            <p>
              Your report remains in Reports / History. Reviewers can start a
              case, verify or reject the observation, and resolve it.
            </p>
          </li>
        </ol>
      </section>
      <section className="card">
        <h2>Know what the map means</h2>
        <p>
          The river centerlines come from OpenStreetMap. They preserve mapped
          coordinates and bends; missing source connections are not invented.
          Open mapping is not an official hydrological survey, and flow through
          reservoirs and tidal reaches may be incomplete.
        </p>
        <p>
          Asset locations and sample observations are labelled as
          demonstrations. Alerts are simulated. Impact priority, reporting
          frequency, and verification status mean different things. No result
          guarantees contamination, concentration, or arrival time.
        </p>
        <a
          className="text-link"
          href="https://www.openstreetmap.org/relation/11778217"
          target="_blank"
          rel="noreferrer"
        >
          View the source Periyar relation ↗
        </a>
      </section>
    </main>
  );
}
