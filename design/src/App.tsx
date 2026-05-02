/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import LandingScreen from './screens/LandingScreen';
import LoginScreen from './screens/LoginScreen';
import MapScreen from './screens/MapScreen';
import StationDetailScreen from './screens/StationDetailScreen';
import RideInProgressScreen from './screens/RideInProgressScreen';
import TripSummaryScreen from './screens/TripSummaryScreen';
import ProfileScreen from './screens/ProfileScreen';
import TripsHistoryScreen from './screens/TripsHistoryScreen';
import PaymentScreen from './screens/PaymentScreen';
import PaymentMethodsScreen from './screens/PaymentMethodsScreen';
import SupportScreen from './screens/SupportScreen';
import BottomNav from './components/BottomNav';

type Screen = 'landing' | 'login' | 'map' | 'station-detail' | 'payment' | 'ride-in-progress' | 'trip-summary' | 'profile' | 'trips-history' | 'payment-methods' | 'support';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>('landing');
  const [currentTab, setCurrentTab] = useState('map');

  const navigate = (screen: Screen) => {
    setCurrentScreen(screen);
    // Sync tab based on screen if needed
    if (screen === 'map') setCurrentTab('map');
    if (screen === 'trips-history') setCurrentTab('trips');
    if (screen === 'profile' || screen === 'payment-methods' || screen === 'support') setCurrentTab('profile');
  };

  const handleTabChange = (tab: string) => {
    setCurrentTab(tab);
    if (tab === 'map') setCurrentScreen('map');
    if (tab === 'trips') setCurrentScreen('trips-history');
    if (tab === 'profile') setCurrentScreen('profile');
    if (tab === 'payments') {
      setCurrentScreen('payment-methods');
    }
  };

  const renderScreen = () => {
    switch (currentScreen) {
      case 'landing':
        return <LandingScreen onStart={() => navigate('login')} />;
      case 'login':
        return <LoginScreen onLogin={() => navigate('map')} />;
      case 'map':
        return <MapScreen onSelectStation={() => navigate('station-detail')} />;
      case 'station-detail':
        return <StationDetailScreen onBack={() => navigate('map')} onUnlock={() => navigate('payment')} />;
      case 'payment':
        return <PaymentScreen onPay={() => navigate('ride-in-progress')} onBack={() => navigate('station-detail')} />;
      case 'ride-in-progress':
        return <RideInProgressScreen onEnd={() => navigate('trip-summary')} />;
      case 'trip-summary':
        return <TripSummaryScreen onFinish={() => navigate('trips-history')} />;
      case 'trips-history':
        return <TripsHistoryScreen onNewTrip={() => navigate('map')} />;
      case 'profile':
        return <ProfileScreen 
          onLogout={() => navigate('landing')} 
          onNavigateHistory={() => navigate('trips-history')}
          onNavigatePayments={() => navigate('payment-methods')}
          onNavigateSupport={() => navigate('support')}
        />;
      case 'payment-methods':
        return <PaymentMethodsScreen onBack={() => navigate('profile')} />;
      case 'support':
        return <SupportScreen onBack={() => navigate('profile')} />;
      default:
        return <MapScreen onSelectStation={() => navigate('station-detail')} />;
    }
  };

  const showNav = !['landing', 'login'].includes(currentScreen);

  return (
    <div className="min-h-screen bg-surface">
      <AnimatePresence mode="wait">
        <motion.div
          key={currentScreen}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="min-h-screen"
        >
          {renderScreen()}
        </motion.div>
      </AnimatePresence>

      {showNav && (
        <BottomNav currentTab={currentTab} setTab={handleTabChange} />
      )}
    </div>
  );
}

