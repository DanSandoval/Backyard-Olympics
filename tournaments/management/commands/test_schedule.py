from django.core.management.base import BaseCommand
from tournaments.models import Tournament
from tournaments.services import SchedulingService

class Command(BaseCommand):
    help = 'Tests the tournament scheduling system'

    def add_arguments(self, parser):
        parser.add_argument('tournament_id', type=int)

    def handle(self, *args, **options):
        try:
            tournament = Tournament.objects.get(pk=options['tournament_id'])
            scheduler = SchedulingService(tournament)
            
            self.stdout.write("Validating tournament setup...")
            is_valid, error = scheduler.validate_tournament_setup()
            if not is_valid:
                self.stdout.write(self.style.ERROR(f"Tournament setup invalid: {error}"))
                return
            
            self.stdout.write("Generating Phase 1 schedule...")
            scheduler.generate_phase1_schedule()
            
            self.stdout.write("Validating generated schedule...")
            violations = scheduler.validate_schedule()
            
            if violations:
                self.stdout.write(self.style.WARNING("Schedule generated with violations:"))
                for violation in violations:
                    self.stdout.write(f"- {violation}")
            else:
                self.stdout.write(self.style.SUCCESS("Schedule generated successfully!"))
                
            # Print schedule summary
            rounds = tournament.rounds.all().order_by('round_number')
            for round in rounds:
                self.stdout.write(f"\nRound {round.round_number}:")
                matchups = round.matchups.all()
                for matchup in matchups:
                    team2_name = matchup.team_2.name if matchup.team_2 else "BYE"
                    self.stdout.write(f"  {matchup.game.name}: {matchup.team_1.name} vs {team2_name}")
                
        except Tournament.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Tournament with ID {options['tournament_id']} not found"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}")) 