import React from 'react'
import PropTypes from 'prop-types'

import config from 'config'

import foundingInitialImage from 'images/funding-initial.png'
import foundingGrowthImage from 'images/funding-growth.png'
import budgetImage from 'images/budget.png'
import demographyImage from 'images/demography.png'
import downloadImage from 'images/download-picto.svg'
import userFeedbackImage from 'images/user-feedback.png'
import userStatsImage from 'images/user-stats.png'
import npsImage from 'images/nps.png'

import {StaticPage} from 'components/static'
import {Colors} from 'components/theme'

const textSectionStyle = {
  backgroundColor: '#fff',
  color: Colors.DARK_TWO,
  display: 'flex',
  flexDirection: 'column',
  fontSize: 16,
  lineHeight: 1.63,
  paddingBottom: 100,
}
const titleStyle = {
  fontSize: 36,
  fontWeight: 'bold',
  padding: '45px 0 40px',
  textAlign: 'center',
}
const sectionTitleStyle = {
  fontSize: 20,
  fontWeight: 'bold',
  marginBottom: 15,
  marginTop: 40,
}
const milestone = {
  border: 'solid 1px',
  borderColor: Colors.SILVER,
  borderRadius: 4,
  flexGrow: 1,
  margin: 5,
  padding: '30px 0',
  textAlign: 'center',
}
const graphStyle = {
  padding: '10px 20px',
}
const milestonesZone = {
  ...graphStyle,
  display: 'flex',
  flexDirection: 'row',
  justifyContent: 'space-between',
  marginTop: 10,
  width: '100%',
}
const excerptStyle = {
  fontStyle: 'italic',
  textAlign: 'center',
}
const milestoneExcerptStyle = {
  ...excerptStyle,
  margin: '30px 20px 0px',
}
const milestoneSubtitle = {
  fontSize: 13,
  fontWeight: 'normal',
  marginTop: 3,
}
const milestoneSurtitle = {
  color: Colors.COOL_GREY,
  fontSize: 10,
  lineHeight: 1,
}
const bulletStyle = {
  marginBottom: 20,
}
const subtitleStyle = {
  fontStyle: 'italic',
  fontWeight: 'bold',
  margin: '0 0 10px',
}
const financeStyle = {
  height: 'auto',
  margin: '30px 0',
  width: '100%',
}
const imageStats = {
  height: 'auto',
  width: '100%',
}
const downloadButtonStyle = {
  backgroundColor: Colors.SKY_BLUE,
  borderRadius: 4,
  boxShadow: '0 2px 3px 0 rgba(0, 0, 0, 0.2)',
  color: '#fff',
  margin: '100 auto 200px auto',
  padding: '15px 20px',
  textDecoration: 'none',
  width: 430,
}


class TransparencyPage extends React.Component {
  static contextTypes = {
    isMobileVersion: PropTypes.bool,
  }

  getTextStyle() {
    const {isMobileVersion} = this.context
    return {
      color: Colors.CHACORAL_GREY,
      lineHeight: 1.63,
      marginBottom: 10,
      padding: isMobileVersion ? '0 50px' : '0 140px',
    }
  }

  makeLink(content, href) {
    const linkStyle = {
      color: Colors.SKY_BLUE,
      textDecoration: 'none',
    }
    return <a style={linkStyle} href={href}> {content} </a>
  }

  renderPageDescription() {
    const {isMobileVersion} = this.context
    const overTitleStyle = {
      fontStyle: 'italic',
      margin: isMobileVersion ? 50 : '50px 140px 0 140px',
      textAlign: 'center',
    }
    return <div style={{...textSectionStyle, paddingBottom: 0}}>
      <div style={overTitleStyle}>
        Cette page répertorie publiquement les informations liées au fonctionnement
        et aux développements de Bob.
      </div>
      <div style={titleStyle}><strong>Impact et métriques</strong></div>
      <div style={this.getTextStyle()}>
        En France, environ une reprise d'emploi sur 10 se fait via une offre d'emploi en
        ligne. Plus que du simple matching, l'enjeu est surtout humain : accompagner chacun
        dans ses choix stratégiques.
        <div style={{fontWeight: 'bold', marginTop: 25}}>
          Notre objectif à travers Bob&nbsp;:
        </div>
        Permettre à chaque individu de prendre le contrôle sur sa stratégie de recherche
        d'emploi, en lui fournissant des pistes de réflexion personnalisées et fondées sur
        les données.
      </div>
    </div>
  }

  renderGeneralMetrics() {
    return <div style={textSectionStyle}>
      <div style={this.getTextStyle()}>
        <div style={sectionTitleStyle}>Métriques générales (au 1er août 2017)</div>
      </div>
      <div style={graphStyle}>
        <img src={userStatsImage} style={imageStats} alt="user statistics" />
      </div>
      <div style={this.getTextStyle()}>
        <div style={sectionTitleStyle}>Travaux en cours</div>
        {config.productName} est en développement actif. Le code est open source et
        {this.makeLink('disponible sur Github', 'https://github.com/bayesimpact/bob-emploi')}.
        Vous pouvez également consulter l' {this.makeLink(
          'historique général du projet',
          'https://github.com/bayesimpact/bob-emploi/blob/master/HISTORY.md')}
        ainsi que {this.makeLink(
          'le changelog complet',
          'https://github.com/bayesimpact/bob-emploi/blob/master/CHANGELOG.md')}.
      </div>
      <div style={milestonesZone}>
        <div style={milestone}>
          <div style={milestoneSurtitle}>FOCUS</div>
          <strong>Expérience utilisateur</strong>
          <div style={{...milestoneSubtitle, color: Colors.GREENISH_TEAL}}>
            Terminé le 19 juillet 2017
          </div>
          <div style={milestoneExcerptStyle}>
            "La proposition de valeur de Bob est claire,
            et l'expérience est cohérente même avec un éventail de
            recommandations plus restreint"
          </div>
        </div>
        <div style={milestone}>
          <div style={milestoneSurtitle}>FOCUS</div>
          <strong>Diversité des recommandations</strong>
          <div style={{...milestoneSubtitle, color: Colors.BUTTERSCOTCH}}>En cours</div>
          <div style={milestoneExcerptStyle}>
            "Bob est capable de recommander suffisamment de types de conseil pour être
            pertinent dans un large éventail de cas."
          </div>
        </div>
        <div style={milestone}>
          <div style={milestoneSurtitle}>FOCUS</div>
          <strong>Algorithmes de scoring</strong>
          <div style={milestoneSubtitle}>&nbsp;</div>
          <div style={milestoneExcerptStyle}>
            "Chaque conseil est contextualisé de façon très personnalisée en fonction du
            profil de la personne."
          </div>
        </div>
      </div>
      <div style={graphStyle}>
        <img src={npsImage} style={imageStats} alt="évaluation par les utilisateurs" />
      </div>
    </div>
  }

  renderUserFeedback() {
    return  <div style={textSectionStyle}>
      <div style={this.getTextStyle()}>
        <div style={sectionTitleStyle}>
          Retours utilisateurs
        </div>
        Nous travaillons à l'amélioration continue de l'impact de Bob au contact
        des utilisateurs.
      </div>
      <div style={graphStyle}>
        <img src={userFeedbackImage} style={imageStats} alt="retour utilisateurs" />
      </div>
      <div style={this.getTextStyle()}>
        <div style={sectionTitleStyle}>
          Axes de travail principaux
        </div>
        <ul>
          <li style={bulletStyle}>
            <span style={subtitleStyle}>Produit :</span> rendre Bob plus pertinent pour plus
            de types de situations différents. La tâche est rendue plus complexe par la faible
            segmentation de notre base utilisateurs de Bob dû à notre volonté de développer
            un outil généraliste.
          </li>
          <li style={bulletStyle}>
            <span style={subtitleStyle}>Distribution</span> : notre stratégie de distribution
            reste embryonnaire
            (presse et bouche-à-oreille). Nous nous concentrons aujourd'hui principalement sur
            l'amélioration de Bob avant de se concentrer plus sur sa distribution, mais cette
            dernière conditionnera in fine notre impact global. Nos budgets ne nous permettant
            pas de faire de grandes campagnes marketing, l'un de notre focus sera d'accroître
            nos liens partenariaux avec les associations et organismes travaillant dans le
            champ de l'emploi.
          </li>
          <li style={bulletStyle}>
            <span style={subtitleStyle}>Écosystème</span> : catalyser l'innovation au sein du
            service public de l'emploi représente une très forte source d'impact au-delà de
            Bob lui-même.
            Nous encourageons notamment la reproduction de certaines fonctionnalités de Bob
            par d'autres acteurs.
          </li>
        </ul>
      </div>
    </div>
  }

  renderDemography() {
    return <div style={textSectionStyle}>
      <div style={titleStyle}><strong>Démographie des utilisateurs</strong></div>
      <div style={this.getTextStyle()}>
        La raison d'être de notre démarche associative est d'apporter de l'aide aux publics
        qui en ont le plus besoin, et pas seulement les publics plus faciles ou plus
        rentables.
        Nous suivons donc divers indicateurs liés à la diversité de la démographie des
        utilisateurs de Bob.
      </div>
      <div style={graphStyle}>
        <img src={demographyImage} style={imageStats} alt="statistiques demographiques" />
      </div>
      <div style={this.getTextStyle()}>
        <div style={sectionTitleStyle}>
          Axes de progression
        </div>
        <ul>
          <li style={bulletStyle}>
            <strong>Se concentrer sur les publics en milieu rural</strong> : Bob reste
            concentré dans les villes, mais nous pensons que l'autonomisation via le numérique
            est d'autant plus pertinente dans les zones moins desservies en services publics.
          </li>
          <li style={bulletStyle}>
            <strong>Rendre Bob plus accessible au regard de la fracture numérique</strong> :
            nous ne sommes pas encore capables de mesurer plus finement l'utilisation de Bob
            par rapport aux différentes dimensions de la fracture numérique (aisance avec
            l'informatique, connectivité à internet, etc.). Nous envisageons notamment de
            nous rapprocher d'acteurs associatifs tels que les missions locales ou
            associations.
          </li>
        </ul>
      </div>
    </div>
  }

  renderFinances() {
    return <div style={textSectionStyle}>
      <div style={titleStyle}><strong>Financement de Bob Emploi</strong></div>
      <div style={this.getTextStyle()}>
        <div>
          Bayes Impact est une association de loi 1901 à but non lucratif. En raison de
          notre volonté  d'inscrire notre initiative dans une démarche citoyenne de service
          public, Bob Emploi ne dispose d'aucun business model et fonctionne de manière
          indépendante. Nous finançons ainsi notre équipe uniquement par des dons et
          subventions, répertoriés ici.
        </div>
        <div style={{marginTop: 20}}>
          Afin d'assurer l'indépendance du projet, aucune contribution philanthropique,
          qu'elle soit en financement ou en nature, ne peut être acceptée si elle fait
          l'objet d'une contrepartie.
        </div>
        <div style={sectionTitleStyle}>
          Sources de Financement
        </div>
        <div style={subtitleStyle}>
          Amorçage
        </div>
        Entre 2015 et 2016, des individus, fondations, ainsi que deux acteurs publics ont
        contribué ensemble 740 000 € de donations et subventions afin de financer l'amorçage
        du projet et les deux premières années d'expérimentation.
        <img src={foundingInitialImage} style={financeStyle} alt="financements initiaux" />
        <div style={subtitleStyle}>
          Croissance de l'impact et pérennisation
        </div>
        En 2017, la fondation La France s'engage (label d'innovation sociale) et la fondation
        Google.org ainsi que la direction RSE du groupe Lafayette ont contribué ensemble
        1 665 000 € en donations répartis sur plusieurs années afin de pérenniser les travaux
        d'amélioration continue de Bob et démultiplier notre impact dans la durée.
        <img src={foundingGrowthImage} style={financeStyle} alt="financements ultérieurs" />
        <div style={sectionTitleStyle}>
          Utilisation du budget
        </div>
      </div>
      <div style={graphStyle}>
        <img src={budgetImage} style={imageStats} alt="budget" />
      </div>
      <div style={downloadButtonStyle}>
        <a
          style={{color: '#fff', padding: 20, textDecoration: 'none'}}
          href="https://www.bob-emploi.fr/assets/rapport-moral-2016.pdf">
          Télécharger le rapport moral annuel de 2016&nbsp;&nbsp;
          <img src={downloadImage} alt="download" />
        </a>
      </div>
    </div>
  }

  render() {
    return <StaticPage page="transparency" style={{backgroundColor: '#fff'}}>
      <div style={{marginLeft: 'auto', marginRight: 'auto', maxWidth: 1000}}>
        {this.renderPageDescription()}
        {this.renderGeneralMetrics()}
        {this.renderUserFeedback()}
        {this.renderDemography()}
        {this.renderFinances()}
      </div>
    </StaticPage>
  }
}

export {TransparencyPage}
