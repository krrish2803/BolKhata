import React, { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface FloatingCoinsProps {
  count?: number;
  areaRadius?: number;
}

export const FloatingCoins: React.FC<FloatingCoinsProps> = ({ count = 28, areaRadius = 7 }) => {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  // Generate particle positions, rotation speeds, and drift offsets
  const particles = useMemo(() => {
    return Array.from({ length: count }, () => ({
      position: new THREE.Vector3(
        (Math.random() - 0.5) * areaRadius * 2,
        (Math.random() - 0.5) * areaRadius * 1.5,
        (Math.random() - 0.5) * 4
      ),
      rotationSpeed: {
        x: (Math.random() - 0.5) * 0.8,
        y: (Math.random() - 0.5) * 1.2,
        z: (Math.random() - 0.5) * 0.5,
      },
      scale: 0.18 + Math.random() * 0.22,
      phase: Math.random() * Math.PI * 2,
    }));
  }, [count, areaRadius]);

  useFrame((state) => {
    if (!meshRef.current) return;
    const t = state.clock.getElapsedTime();

    particles.forEach((p, i) => {
      // Floating sinusoidal motion
      const yOffset = Math.sin(t * 0.8 + p.phase) * 0.4;
      dummy.position.set(p.position.x, p.position.y + yOffset, p.position.z);
      
      dummy.rotation.x = t * p.rotationSpeed.x;
      dummy.rotation.y = t * p.rotationSpeed.y;
      dummy.rotation.z = t * p.rotationSpeed.z;
      
      dummy.scale.set(p.scale, p.scale, p.scale * 0.25); // Coin cylinder profile
      dummy.updateMatrix();

      meshRef.current!.setMatrixAt(i, dummy.matrix);
    });

    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, count]}>
      {/* Golden Indian rupee coin token geometry */}
      <cylinderGeometry args={[1, 1, 0.4, 24]} />
      <meshStandardMaterial
        color="#F5B700"
        roughness={0.25}
        metalness={0.85}
        emissive="#B38600"
        emissiveIntensity={0.2}
      />
    </instancedMesh>
  );
};
