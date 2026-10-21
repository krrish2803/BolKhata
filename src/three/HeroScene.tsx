import React, { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { MeshDistortMaterial, Float } from '@react-three/drei';
import * as THREE from 'three';
import { FloatingCoins } from './Particles';

interface HeroSceneInnerProps {
  scrollProgress: number; // 0 (top) to 1 (scrolled through hero)
  isLowPower?: boolean;
}

const HeroMeshScene: React.FC<HeroSceneInnerProps> = ({ scrollProgress, isLowPower = false }) => {
  const orbRef = useRef<THREE.Mesh>(null);
  const bookRef = useRef<THREE.Group>(null);
  const leftCoverRef = useRef<THREE.Group>(null);
  const rightCoverRef = useRef<THREE.Group>(null);
  const ledgerRowsRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();

    // 1. Orb animation: pulses audio waveform
    if (orbRef.current) {
      // As scrollProgress increases (0 -> 1), orb sinks, shrinks, and "pours" into the ledger
      const orbScale = Math.max(0, (1 - scrollProgress * 1.5) * (1.1 + Math.sin(t * 3.5) * 0.08));
      const orbY = 0.5 - scrollProgress * 2.2;
      orbRef.current.position.y = orbY;
      orbRef.current.position.x = Math.sin(t * 1.2) * 0.15;
      orbRef.current.scale.setScalar(orbScale);
      orbRef.current.rotation.y = t * 0.4;
      orbRef.current.rotation.x = Math.sin(t * 0.5) * 0.2;
    }

    // 2. Ledger Book animation:
    // Opens smoothly as scrollProgress transitions from 0.15 to 0.7
    if (bookRef.current) {
      const bookProgress = THREE.MathUtils.clamp((scrollProgress - 0.1) / 0.6, 0, 1);
      // Gentle book tilt
      bookRef.current.rotation.x = 0.45 - bookProgress * 0.15 + Math.sin(t * 0.8) * 0.04;
      bookRef.current.rotation.y = -0.3 + bookProgress * 0.3 + Math.cos(t * 0.7) * 0.04;
      bookRef.current.position.y = -1.4 + bookProgress * 0.6;
      
      // Book covers opening like traditional Indian bahi khata
      if (leftCoverRef.current && rightCoverRef.current) {
        const openAngle = THREE.MathUtils.lerp(0.08, 0.45, bookProgress);
        leftCoverRef.current.rotation.y = -openAngle;
        rightCoverRef.current.rotation.y = openAngle;
      }
    }

    // 3. Ledger rows floating up out of book
    if (ledgerRowsRef.current) {
      const rowProgress = THREE.MathUtils.clamp((scrollProgress - 0.25) / 0.6, 0, 1);
      ledgerRowsRef.current.position.y = -0.8 + rowProgress * 1.4;
      ledgerRowsRef.current.scale.setScalar(THREE.MathUtils.lerp(0.1, 1, rowProgress));
      
      // Subtle float wave
      ledgerRowsRef.current.children.forEach((child, idx) => {
        child.position.y = (idx * 0.42) + Math.sin(t * 1.8 + idx) * 0.05;
        child.position.x = Math.sin(t * 1.2 + idx * 0.7) * 0.04;
      });
    }
  });

  return (
    <>
      <ambientLight intensity={0.8} />
      <directionalLight position={[5, 8, 5]} intensity={1.5} color="#FFF8EC" />
      <pointLight position={[-4, -2, 2]} intensity={0.9} color="#F5B700" />
      <pointLight position={[3, 3, -2]} intensity={0.6} color="#2E9E5B" />

      {/* Ambient instanced gold rupee coins */}
      <FloatingCoins count={isLowPower ? 12 : 24} areaRadius={6} />

      {/* Voice Glowing Orb */}
      <Float speed={2} rotationIntensity={0.5} floatIntensity={0.6}>
        <mesh ref={orbRef} position={[0, 0.5, 0]}>
          <sphereGeometry args={[1, isLowPower ? 32 : 64, isLowPower ? 32 : 64]} />
          <MeshDistortMaterial
            color="#F5B700"
            emissive="#B38600"
            emissiveIntensity={0.4}
            roughness={0.2}
            metalness={0.5}
            distort={0.42}
            speed={3.2}
          />
        </mesh>
      </Float>

      {/* 3D Ledger Book (Low-poly red-bound Indian bahi khata) */}
      <group ref={bookRef} position={[0, -1.4, 0]}>
        {/* Spine */}
        <mesh position={[0, 0, 0]}>
          <boxGeometry args={[0.3, 0.45, 2.6]} />
          <meshStandardMaterial color="#B32424" roughness={0.4} />
        </mesh>

        {/* Left Page & Cover */}
        <group ref={leftCoverRef} position={[-0.15, 0, 0]}>
          <mesh position={[-0.95, 0.02, 0]}>
            {/* Paper block */}
            <boxGeometry args={[1.9, 0.35, 2.5]} />
            <meshStandardMaterial color="#FFF8EC" roughness={0.7} />
          </mesh>
          {/* Crimson cover */}
          <mesh position={[-0.97, -0.19, 0]}>
            <boxGeometry args={[1.96, 0.06, 2.56]} />
            <meshStandardMaterial color="#8F1515" roughness={0.3} />
          </mesh>
          {/* Gold embossed bahi border line */}
          <mesh position={[-0.95, 0.2, 0]}>
            <boxGeometry args={[1.7, 0.01, 2.3]} />
            <meshStandardMaterial color="#F5B700" metalness={0.6} roughness={0.3} />
          </mesh>
        </group>

        {/* Right Page & Cover */}
        <group ref={rightCoverRef} position={[0.15, 0, 0]}>
          <mesh position={[0.95, 0.02, 0]}>
            <boxGeometry args={[1.9, 0.35, 2.5]} />
            <meshStandardMaterial color="#FFF8EC" roughness={0.7} />
          </mesh>
          <mesh position={[0.97, -0.19, 0]}>
            <boxGeometry args={[1.96, 0.06, 2.56]} />
            <meshStandardMaterial color="#8F1515" roughness={0.3} />
          </mesh>
          <mesh position={[0.95, 0.2, 0]}>
            <boxGeometry args={[1.7, 0.01, 2.3]} />
            <meshStandardMaterial color="#F5B700" metalness={0.6} roughness={0.3} />
          </mesh>
        </group>

        {/* Floating Ledger Rows that rise from the open book */}
        <group ref={ledgerRowsRef} position={[0, 0.4, 0.3]}>
          {/* Row 1: Sale entry */}
          <mesh position={[0, 0, 0]}>
            <boxGeometry args={[2.5, 0.28, 0.05]} />
            <meshStandardMaterial color="#0F1B2D" roughness={0.3} />
          </mesh>
          {/* Row 2: Paid chip */}
          <mesh position={[-0.3, 0.42, 0.1]}>
            <boxGeometry args={[1.8, 0.24, 0.05]} />
            <meshStandardMaterial color="#2E9E5B" roughness={0.4} />
          </mesh>
          {/* Row 3: Udhaar chip */}
          <mesh position={[0.3, 0.84, 0.15]}>
            <boxGeometry args={[1.6, 0.24, 0.05]} />
            <meshStandardMaterial color="#D64545" roughness={0.4} />
          </mesh>
        </group>
      </group>
    </>
  );
};

export const HeroScene: React.FC<{ scrollProgress?: number }> = ({ scrollProgress = 0 }) => {
  return (
    <div className="relative w-full h-[400px] sm:h-[480px] lg:h-[580px] pointer-events-none select-none">
      <Canvas
        camera={{ position: [0, 0.5, 5.2], fov: 42 }}
        dpr={[1, 2]} // Cap devicePixelRatio at 2 as required
        gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
      >
        <HeroMeshScene scrollProgress={scrollProgress} />
      </Canvas>
    </div>
  );
};
