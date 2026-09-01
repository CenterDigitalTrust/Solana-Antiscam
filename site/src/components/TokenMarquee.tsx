'use client';
import { motion } from 'framer-motion';
import { TokenData } from '@/hooks/useTokens';

export default function TokenMarquee({ tokens }: { tokens: TokenData[] }) {
  if (tokens.length === 0) return null;

  return (
    <div className="w-full bg-ink text-beige-0 border-y border-rule overflow-hidden flex whitespace-nowrap py-2 relative">
      <div className="absolute left-0 top-0 bottom-0 w-8 bg-gradient-to-r from-ink to-transparent z-10"></div>
      <div className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-ink to-transparent z-10"></div>
      
      <motion.div 
        className="flex gap-8 items-center"
        animate={{ x: [0, -1035] }}
        transition={{ ease: 'linear', duration: 20, repeat: Infinity }}
      >
        {/* Duplicate array for seamless loop */}
        {[...tokens, ...tokens].slice(0, 40).map((token, i) => (
          <div key={i} className="flex items-center gap-2 font-mono text-sm">
            <span className={token.status === 'SUCCESS' ? 'text-olive' : token.status === 'REJECT' ? 'text-rust' : 'text-ochre'}>
              {token.status === 'SUCCESS' ? '●' : token.status === 'REJECT' ? '☠' : '○'}
            </span>
            <span className="font-bold">${token.ticker}</span>
            <span className="text-beige-0/50">Score: {token.score}</span>
          </div>
        ))}
      </motion.div>
    </div>
  );
}
