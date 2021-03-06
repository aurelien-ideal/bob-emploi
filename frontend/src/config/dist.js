'use strict'

const config = {
  // This is configured in https://www.amplitude.com/app/159830/manage.
  amplitudeToken: '277314ee2eade2cb083c0d612107dcc6',
  donationUrl: 'https://www.helloasso.com/associations/bayes-impact-france/formulaires/3',
  // This is configured in:
  // https://developers.facebook.com/apps/1576288225722008/dashboard/
  // TODO(pascal): Add a way to use a different one on the demo
  // ('1048782155234293').
  facebookSSOAppId: '1576288225722008',
  githubSourceLink: 'https://github.com/bayesimpact/bob-emploi',
  // This is configured in:
  // https://console.cloud.google.com/apis/credentials?project=bob-emploi
  // When serving from a new host or a new port, you'll need to update the page
  // above to include it as an authorized Javascript source.
  // TODO(pascal): Add a way to use a different one on the demo
  // (1052239456978-tgef7mpqd3qoq723hag0v45035nqnivt.apps.googleusercontent.com),
  googleSSOClientId: '524962411351-hl5h7ap6mbvsj4of7pl6i51heqsuqtgo.apps.googleusercontent.com',
  // This is configured in:
  // https://analytics.google.com/analytics/web
  googleUAID: 'UA-97637389-1',
  helpRequestUrl: 'https://aide.bob-emploi.fr/hc/fr/requests/new',
  jobGroupImageUrl: 'https://storage.gra1.cloud.ovh.net/v1/AUTH_7b9ade05d5f84f719adc2cbc76c07eec/Cover%20Images/ROME_ID.jpg',
  productName: 'Bob Emploi',
  // This is configured in:
  // https://sentry.io/bayes-impact/bob-emploi/settings/install/javascript-react/
  // You need to log in with florian@bayes.org
  // Ask password to Florian, as we have only one user in our current plan.
  // The dashboard is in:
  // https://sentry.io/bayes-impact/bob-emploi/
  sentryDSN: 'https://213e063a07514ab78a6e8f0bf88cb63b@sentry.io/191228',
  zendeskDomain: 'aide.bob-emploi.fr',
}

export default config
