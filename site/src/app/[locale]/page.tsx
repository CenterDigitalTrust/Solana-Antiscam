import Header from '@/components/Header';
import Hero from '@/components/Hero';
import TerminalFeed from '@/components/TerminalFeed';
import StatsBar from '@/components/StatsBar';
import MethodologyGrid from '@/components/MethodologyGrid';
import MonitoringTable from '@/components/MonitoringTable';
import GrowthTable from '@/components/GrowthTable';
import QuarantineGrid from '@/components/QuarantineGrid';
import About from '@/components/About';
import Footer from '@/components/Footer';

export default function Home() {
  return (
    <div className="min-h-screen bg-beige-0 flex flex-col items-center overflow-x-hidden selection:bg-ink selection:text-paper">
      <Header />
      <main className="w-full">
        <Hero />
        <TerminalFeed />
        <StatsBar />
        <MethodologyGrid />
        <MonitoringTable />
        <GrowthTable />
        <QuarantineGrid />
        <About />
      </main>
      <Footer />
    </div>
  );
}
