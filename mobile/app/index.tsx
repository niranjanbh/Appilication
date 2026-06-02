import { StyleSheet, Text, View } from 'react-native';

export default function HomeScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.heading}>Kyros</Text>
      <Text style={styles.subtext}>Doctor-first hormonal health</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FAF1E4',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  heading: {
    fontSize: 42,
    color: '#0F3D2E',
    fontWeight: '500',
  },
  subtext: {
    fontSize: 15,
    color: '#6B6B68',
    marginTop: 8,
  },
});
