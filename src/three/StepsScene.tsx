import React, { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { MeshDistortMaterial, Text } from '@react-three/drei';
import * as THREE from 'three';

interface StepsSceneInnerProps {
  activeStep: number; // 0 to 4
}

const StepsSceneMesh: React.FC<StepsSceneInnerProps> = ({ activeStep }) => {
  const groupRef = useRef<THREE.Group>(null);
  const orbRef = useRef<THREE.Mesh>(null);
  const bubbleRef = useRef<THREE.Group>(null);
  const chipsRef = useRef<THREE.Group>(null);
  const cardRef = useRef<THREE.Group>(null);
  const phoneRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    const targetY = [0, 0, 0, 0, 0][activeStep] || 0;
    
    // Smooth camera target rotation/position easing
    if (groupRef.current) {
      groupRef.current.rotation.y = THREE.MathUtils.lerp(
        groupRef.current.rotation.y,
        (activeStep * 0.25) + Math.sin(t * 0.5) * 0.05,
        0.08
      );
      groupRef.current.position.y = THREE.MathUtils.lerp(
        groupRef.current.position.y,
        targetY,
        0.08
      );
    }

    // Individual step transforms & visibility interpolation
    // Step 0: Mic Orb pulsing
    if (orbRef.current) {
      const active = activeStep === 0;
      const targetScale = active ? (1.3 + Math.sin(t * 4) * 0.12) : 0;
      orbRef.current.scale.setScalar(THREE.MathUtils.lerp(orbRef.current.scale.x, targetScale, 0.1));
    }

    // Step 1: Text bubble of Hinglish sentence
    if (bubbleRef.current) {
      const active = activeStep === 1;
      const targetScale = active ? 1 : 0;
      bubbleRef.current.scale.setScalar(THREE.MathUtils.lerp(bubbleRef.current.scale.x, targetScale, 0.1));
      bubbleRef.current.position.y = Math.sin(t * 1.5) * 0.08;
    }

    // Step 2: Sentence splitting into 5 labelled chips
    if (chipsRef.current) {
      const active = activeStep === 2;
      const targetScale = active ? 1 : 0;
      chipsRef.current.scale.setScalar(THREE.MathUtils.lerp(chipsRef.current.scale.x, targetScale, 0.1));
      chipsRef.current.children.forEach((child, i) => {
        child.position.y = (i - 2) * 0.45 + Math.sin(t * 2 + i) * 0.04;
      });
    }

    // Step 3: Confirm card flipping
    if (cardRef.current) {
      const active = activeStep === 3;
      const targetScale = active ? 1 : 0;
      cardRef.current.scale.setScalar(THREE.MathUtils.lerp(cardRef.current.scale.x, targetScale, 0.1));
      if (active) {
        cardRef.current.rotation.y = THREE.MathUtils.lerp(cardRef.current.rotation.y, Math.sin(t * 1.2) * 0.35, 0.05);
      }
    }

    // Step 4: Phone with WhatsApp-style receipt
    if (phoneRef.current) {
      const active = activeStep === 4;
      const targetScale = active ? 1 : 0;
      phoneRef.current.scale.setScalar(THREE.MathUtils.lerp(phoneRef.current.scale.x, targetScale, 0.1));
      phoneRef.current.rotation.z = Math.sin(t * 1.2) * 0.03;
    }
  });

  return (
    <>
      <ambientLight intensity={0.9} />
      <directionalLight position={[4, 6, 4]} intensity={1.4} color="#FFF8EC" />
      <pointLight position={[-3, 2, 2]} intensity={0.8} color="#F5B700" />
      <pointLight position={[3, -2, 2]} intensity={0.5} color="#2E9E5B" />

      <group ref={groupRef}>
        {/* STEP 0: Glowing Mic Orb */}
        <mesh ref={orbRef} position={[0, 0, 0]}>
          <sphereGeometry args={[1, 48, 48]} />
          <MeshDistortMaterial
            color="#F5B700"
            emissive="#B38600"
            emissiveIntensity={0.5}
            distort={0.45}
            speed={4}
            roughness={0.2}
          />
        </mesh>

        {/* STEP 1: Spoken Text speech bubble plane */}
        <group ref={bubbleRef} position={[0, 0, 0]} scale={0}>
          {/* Rounded bubble backing */}
          <mesh position={[0, 0, 0]}>
            <boxGeometry args={[3.2, 1.6, 0.12]} />
            <meshStandardMaterial color="#0F1B2D" roughness={0.3} />
          </mesh>
          <mesh position={[0, -0.9, 0]} rotation={[0, 0, Math.PI / 4]}>
            <boxGeometry args={[0.35, 0.35, 0.1]} />
            <meshStandardMaterial color="#0F1B2D" />
          </mesh>
          <Text
            position={[0, 0.25, 0.08]}
            fontSize={0.2}
            maxWidth={2.8}
            color="#F5B700"
            anchorX="center"
            anchorY="middle"
          >
            "Sharma ji ko do shirt aur..."
          </Text>
          <Text
            position={[0, -0.25, 0.08]}
            fontSize={0.16}
            maxWidth={2.8}
            color="#FFF8EC"
            anchorX="center"
            anchorY="middle"
          >
            4200 bill, 2000 diya, baaki udhaar
          </Text>
        </group>

        {/* STEP 2: Five Extruded Labelled Chips */}
        <group ref={chipsRef} position={[0, 0, 0]} scale={0}>
          {/* Chip 1: Customer */}
          <group position={[0, 0.9, 0]}>
            <mesh>
              <boxGeometry args={[2.8, 0.36, 0.08]} />
              <meshStandardMaterial color="#0F1B2D" />
            </mesh>
            <Text position={[-0.8, 0, 0.06]} fontSize={0.13} color="#F5B700">Customer:</Text>
            <Text position={[0.4, 0, 0.06]} fontSize={0.13} color="#FFF8EC">Sharma ji</Text>
          </group>

          {/* Chip 2: Items */}
          <group position={[0, 0.45, 0]}>
            <mesh>
              <boxGeometry args={[2.8, 0.36, 0.08]} />
              <meshStandardMaterial color="#0F1B2D" />
            </mesh>
            <Text position={[-0.8, 0, 0.06]} fontSize={0.13} color="#F5B700">Items:</Text>
            <Text position={[0.4, 0, 0.06]} fontSize={0.13} color="#FFF8EC">2 Shirt, 1 Trouser</Text>
          </group>

          {/* Chip 3: Total */}
          <group position={[0, 0, 0]}>
            <mesh>
              <boxGeometry args={[2.8, 0.36, 0.08]} />
              <meshStandardMaterial color="#1B2C47" />
            </mesh>
            <Text position={[-0.8, 0, 0.06]} fontSize={0.13} color="#FFF8EC">Total Bill:</Text>
            <Text position={[0.4, 0, 0.06]} fontSize={0.15} color="#F5B700" fontWeight="bold">₹4,200</Text>
          </group>

          {/* Chip 4: Paid */}
          <group position={[0, -0.45, 0]}>
            <mesh>
              <boxGeometry args={[2.8, 0.36, 0.08]} />
              <meshStandardMaterial color="#2E9E5B" />
            </mesh>
            <Text position={[-0.8, 0, 0.06]} fontSize={0.13} color="#FFF8EC">Paid:</Text>
            <Text position={[0.4, 0, 0.06]} fontSize={0.15} color="#FFF8EC">₹2,000 (Cash)</Text>
          </group>

          {/* Chip 5: Due / Udhaar */}
          <group position={[0, -0.9, 0]}>
            <mesh>
              <boxGeometry args={[2.8, 0.36, 0.08]} />
              <meshStandardMaterial color="#D64545" />
            </mesh>
            <Text position={[-0.8, 0, 0.06]} fontSize={0.13} color="#FFF8EC">Udhaar Added:</Text>
            <Text position={[0.4, 0, 0.06]} fontSize={0.15} color="#FFF8EC">₹2,200</Text>
          </group>
        </group>

        {/* STEP 3: Confirm Card Flipping */}
        <group ref={cardRef} position={[0, 0, 0]} scale={0}>
          <mesh position={[0, 0, 0]}>
            <boxGeometry args={[3, 2.2, 0.1]} />
            <meshStandardMaterial color="#FFF8EC" roughness={0.4} />
          </mesh>
          {/* Green verification ribbon */}
          <mesh position={[0, 0.85, 0.06]}>
            <boxGeometry args={[2.6, 0.28, 0.02]} />
            <meshStandardMaterial color="#2E9E5B" />
          </mesh>
          <Text position={[0, 0.85, 0.08]} fontSize={0.13} color="#FFFFFF">
            CONFIRM ENTRY · SAHI HAI?
          </Text>
          <Text position={[0, 0.25, 0.06]} fontSize={0.22} color="#0F1B2D">
            Sharma ji · ₹4,200
          </Text>
          <Text position={[0, -0.15, 0.06]} fontSize={0.15} color="#2E9E5B">
            Paid ₹2,000 | Due ₹2,200
          </Text>
          {/* Action pill */}
          <mesh position={[0, -0.65, 0.06]}>
            <boxGeometry args={[1.8, 0.38, 0.02]} />
            <meshStandardMaterial color="#F5B700" />
          </mesh>
          <Text position={[0, -0.65, 0.08]} fontSize={0.14} color="#0F1B2D">
            ✓ Tap to Save
          </Text>
        </group>

        {/* STEP 4: Smartphone with WhatsApp Receipt Bubble */}
        <group ref={phoneRef} position={[0, 0, 0]} scale={0}>
          {/* Phone body */}
          <mesh position={[0, 0, -0.05]}>
            <boxGeometry args={[2.2, 3.8, 0.16]} />
            <meshStandardMaterial color="#0F1B2D" roughness={0.2} metalness={0.6} />
          </mesh>
          {/* Screen surface */}
          <mesh position={[0, 0, 0.04]}>
            <boxGeometry args={[2.0, 3.5, 0.02]} />
            <meshStandardMaterial color="#EFEAE2" />
          </mesh>
          {/* WhatsApp top bar */}
          <mesh position={[0, 1.48, 0.06]}>
            <boxGeometry args={[2.0, 0.45, 0.02]} />
            <meshStandardMaterial color="#075E54" />
          </mesh>
          <Text position={[-0.2, 1.48, 0.08]} fontSize={0.14} color="#FFFFFF">
            Sharma ji (WhatsApp)
          </Text>
          {/* WhatsApp Chat Bubble */}
          <mesh position={[0, 0.2, 0.06]}>
            <boxGeometry args={[1.7, 1.8, 0.02]} />
            <meshStandardMaterial color="#DCF8C6" />
          </mesh>
          <Text position={[0, 0.85, 0.08]} fontSize={0.13} color="#0F1B2D" fontWeight="bold">
            🧾 BolKhata Receipt
          </Text>
          <Text position={[0, 0.5, 0.08]} fontSize={0.11} color="#333333">
            2x Shirt, 1x Trouser
          </Text>
          <Text position={[0, 0.2, 0.08]} fontSize={0.12} color="#0F1B2D">
            Total Bill: ₹4,200
          </Text>
          <Text position={[0, -0.1, 0.08]} fontSize={0.11} color="#2E9E5B">
            Paid: ₹2,000 (Cash)
          </Text>
          <Text position={[0, -0.4, 0.08]} fontSize={0.13} color="#D64545" fontWeight="bold">
            Baaki Udhaar: ₹2,200
          </Text>
          {/* Ready to send WhatsApp button badge */}
          <mesh position={[0, -1.2, 0.06]}>
            <boxGeometry args={[1.5, 0.35, 0.02]} />
            <meshStandardMaterial color="#25D366" />
          </mesh>
          <Text position={[0, -1.2, 0.08]} fontSize={0.13} color="#FFFFFF">
            ➤ Sent on WhatsApp
          </Text>
        </group>
      </group>
    </>
  );
};

export const StepsScene: React.FC<{ activeStep: number }> = ({ activeStep }) => {
  return (
    <div className="w-full h-full min-h-[380px] md:min-h-[500px]">
      <Canvas
        camera={{ position: [0, 0, 4.8], fov: 42 }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true }}
      >
        <StepsSceneMesh activeStep={activeStep} />
      </Canvas>
    </div>
  );
};
